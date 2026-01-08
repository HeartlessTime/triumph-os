from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import os

from app.database import get_db
from app.auth import get_current_user, DEMO_MODE
from app.models import (
    Opportunity, OpportunityScope, Account, Contact,
    User, ScopePackage, Estimate, Activity, Task, Document
)
from app.models import Document as DocModel
from app.services.followup import calculate_next_followup, get_followup_status
from app.demo_data import get_all_demo_opportunities, get_demo_accounts

router = APIRouter(prefix="/opportunities", tags=["opportunities"])
templates = Jinja2Templates(directory="app/templates")


def update_opportunity_followup(opportunity: Opportunity, today: date = None):
    """Update the next_followup date for an opportunity."""
    if today is None:
        today = date.today()
    
    opportunity.next_followup = calculate_next_followup(
        stage=opportunity.stage,
        last_contacted=opportunity.last_contacted,
        bid_date=opportunity.bid_date,
        today=today
    )


@router.get("", response_class=HTMLResponse)
async def list_opportunities(
    request: Request,
    search: str = None,
    stage: str = None,
    owner_id: int = None,
    estimator_id: int = None,
    gc_id: int = None,
    end_user_account_id: int = None,
    db: Session = Depends(get_db)
):
    """List all opportunities with optional filtering."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/opportunities", status_code=303)

    today = date.today()

    # DEMO MODE: Use demo data
    if DEMO_MODE or db is None:
        opportunities = get_all_demo_opportunities()
        accounts = get_demo_accounts()

        # Apply filters to demo data
        if search:
            search_lower = search.lower()
            opportunities = [o for o in opportunities if search_lower in o.name.lower()]

        if stage:
            opportunities = [o for o in opportunities if o.stage == stage]

        if owner_id:
            opportunities = [o for o in opportunities if o.owner_id == owner_id]

        if estimator_id:
            opportunities = [o for o in opportunities if o.assigned_estimator_id == estimator_id]

        if gc_id:
            opportunities = [o for o in opportunities if getattr(o, 'gcs', None) and gc_id in (o.gcs or [])]

        if end_user_account_id:
            opportunities = [o for o in opportunities if getattr(o, 'end_user_account_id', None) == end_user_account_id]

        # Sort by bid date
        opportunities.sort(key=lambda o: (o.bid_date if o.bid_date else date(9999, 12, 31), o.name))

        # Add followup status
        for opp in opportunities:
            opp.followup_status = get_followup_status(opp.next_followup, today)

        users = []  # No users list in demo mode
    else:
        query = db.query(Opportunity).join(Account)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Opportunity.name.ilike(search_term),
                    Account.name.ilike(search_term),
                )
            )

        if stage:
            query = query.filter(Opportunity.stage == stage)

        if owner_id:
            query = query.filter(Opportunity.owner_id == owner_id)

        if estimator_id:
            query = query.filter(Opportunity.assigned_estimator_id == estimator_id)

        opportunities = query.order_by(Opportunity.bid_date.nullslast(), Opportunity.name).all()

        # If filtering by GC or end-user, apply Python-side filters (JSON fields can't be queried portably here)
        if gc_id:
            opportunities = [o for o in opportunities if o.gcs and gc_id in (o.gcs or [])]
        if end_user_account_id:
            opportunities = [o for o in opportunities if o.end_user_account_id == end_user_account_id]

        accounts = db.query(Account).order_by(Account.name).all()

        # Add followup status to each
        for opp in opportunities:
            opp.followup_status = get_followup_status(opp.next_followup, today)

        users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
    
    return templates.TemplateResponse("opportunities/list.html", {
        "request": request,
        "user": user,
        "opportunities": opportunities,
        "users": users,
        "stages": Opportunity.STAGE_NAMES,
        "search": search,
        "stage": stage,
        "owner_id": owner_id,
        "estimator_id": estimator_id,
        "gc_id": gc_id,
        "end_user_account_id": end_user_account_id,
        "accounts": accounts,
    })


@router.get("/intake", response_class=HTMLResponse)
async def intake_form(
    request: Request,
    account_id: int = None,
    db: Session = Depends(get_db)
):
    """Display opportunity intake form."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/opportunities/intake", status_code=303)

    # DEMO MODE: Show notice instead of form
    if DEMO_MODE or db is None:
        return templates.TemplateResponse("demo_mode_notice.html", {
            "request": request,
            "user": user,
            "feature": "Create New Opportunity",
            "message": "Creating new opportunities is disabled in demo mode. Explore the existing demo opportunities instead.",
            "back_url": "/opportunities",
        })

    accounts = db.query(Account).order_by(Account.name).all()
    scope_packages = db.query(ScopePackage).filter(
        ScopePackage.is_active == True
    ).order_by(ScopePackage.sort_order).all()

    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
    sales_users = [u for u in users if u.role in ('Sales', 'Admin')]
    estimators = [u for u in users if u.role in ('Estimator', 'Admin')]

    # Get contacts for selected account
    contacts = []
    if account_id:
        contacts = db.query(Contact).filter(
            Contact.account_id == account_id
        ).order_by(Contact.last_name).all()
    
    return templates.TemplateResponse("opportunities/intake.html", {
        "request": request,
        "user": user,
        "accounts": accounts,
        "scope_packages": scope_packages,
        "sales_users": sales_users,
        "estimators": estimators,
        "contacts": contacts,
        "selected_account_id": account_id,
        "stages": Opportunity.STAGES,
        "sources": Opportunity.SOURCES,
    })


@router.post("/intake")
async def create_opportunity(
    request: Request,
    account_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(None),
    stage: str = Form("Prospecting"),
    lv_value: str = Form(None),
    hdd_value: str = Form(None),
    bid_date: str = Form(None),
    bid_time: str = Form(None),
    bid_type: str = Form(None),
    submission_method: str = Form(None),
    bid_form_required: bool = Form(False),
    bond_required: bool = Form(False),
    prevailing_wage: str = Form(None),
    project_type: str = Form(None),
    rebid: bool = Form(False),
    known_risks: str = Form(None),
    plans: UploadFile = File(None),
    addenda: UploadFile = File(None),
    previous_estimate_file: UploadFile = File(None),
    owner_id: int = Form(None),
    assigned_estimator_id: int = Form(None),
    primary_contact_id: int = Form(None),
    source: str = Form(None),
    notes: str = Form(None),
    gc_ids: List[int] = Form(default=[]),
    related_contact_ids: List[int] = Form(default=[]),
    quick_links_text: str = Form(None),
    end_user_account_id: int = Form(None),
    scope_ids: List[int] = Form(default=[]),
    scope_names: List[str] = Form(default=[]),
    scope_other_text: str = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new opportunity from intake form."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if DEMO_MODE or db is None:
        return RedirectResponse(url="/opportunities", status_code=303)
    
    # Parse values (strip commas if present)
    def clean_num(s: Optional[str]):
        if not s:
            return None
        return s.replace(',', '')

    lv_value_decimal = Decimal(clean_num(lv_value)) if lv_value and clean_num(lv_value) else None
    hdd_value_decimal = Decimal(clean_num(hdd_value)) if hdd_value and clean_num(hdd_value) else None
    bid_date_parsed = datetime.strptime(bid_date, "%Y-%m-%d").date() if bid_date else None
    bid_time_parsed = None
    if bid_time:
        try:
            bid_time_parsed = datetime.strptime(bid_time, "%H:%M").time()
        except Exception:
            bid_time_parsed = None
    
    # Get default probability for stage — treat as optional and default to 0
    probability = Opportunity.STAGE_PROBABILITIES.get(stage, 0)
    
    # known_risks is optional now

    # Ensure estimator assignment rules: if not provided, auto-assign a default estimator
    if not assigned_estimator_id:
        default_estimator = db.query(User).filter(User.is_active == True).filter(User.role.in_(['Estimator','Admin'])).order_by(User.full_name).first()
        if default_estimator:
            assigned_estimator_id = default_estimator.id
        else:
            raise HTTPException(status_code=400, detail="No estimator available to assign; please select an estimator")

    # If this is a rebid, require previous estimate upload
    if rebid and not previous_estimate_file:
        raise HTTPException(status_code=400, detail="Rebid selected: a previous estimate file must be uploaded")

    # Create opportunity
    opportunity = Opportunity(
        account_id=account_id,
        name=name,
        description=description or None,
        stage=stage,
        probability=probability,
        lv_value=lv_value_decimal,
        hdd_value=hdd_value_decimal,
        bid_date=bid_date_parsed,
        bid_time=bid_time_parsed,
        bid_type=bid_type or None,
        submission_method=submission_method or None,
        bid_form_required=bool(bid_form_required),
        bond_required=bool(bond_required),
        prevailing_wage=prevailing_wage or None,
        owner_id=owner_id or user.id,
        assigned_estimator_id=assigned_estimator_id or None,
        primary_contact_id=primary_contact_id or None,
        source=source or None,
        notes=notes or None,
        estimating_checklist=Opportunity.DEFAULT_CHECKLIST.copy(),
        last_contacted=date.today(),
        known_risks=known_risks,
        project_type=project_type or None,
        rebid=bool(rebid),
        gcs=gc_ids or None,
        related_contact_ids=related_contact_ids or None,
        quick_links=[l.strip() for l in quick_links_text.splitlines() if l.strip()] if quick_links_text else None,
        end_user_account_id=end_user_account_id or None,
    )
    
    # Calculate initial followup
    update_opportunity_followup(opportunity)
    
    db.add(opportunity)
    db.flush()
    
    # Add scope packages (by ids and/or names). Ensure normalized links.
    for scope_id in scope_ids:
        scope_link = OpportunityScope(
            opportunity_id=opportunity.id,
            scope_package_id=scope_id
        )
        db.add(scope_link)

    # If scope names provided, find-or-create ScopePackage entries and link
    for sname in scope_names:
        if not sname:
            continue
        # If user provided 'Other' free text, include it
        if sname == 'Other' and scope_other_text:
            sname = scope_other_text.strip()
        sp = db.query(ScopePackage).filter(ScopePackage.name == sname).first()
        if not sp:
            sp = ScopePackage(name=sname, description=None, is_active=True)
            db.add(sp)
            db.flush()
        scope_link = OpportunityScope(opportunity_id=opportunity.id, scope_package_id=sp.id)
        db.add(scope_link)
    
    db.commit()

    # Handle uploaded files: plans, addenda, previous_estimate_file
    def save_upload(upload_file, dtype):
        if not upload_file:
            return
        # leverage documents route logic inline
        UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
        import uuid, shutil
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        original_filename = upload_file.filename
        ext = os.path.splitext(original_filename)[1] if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        file_size = os.path.getsize(file_path)
        doc = DocModel(
            opportunity_id=opportunity.id,
            name=original_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=upload_file.content_type,
            document_type=dtype,
            uploaded_by_id=user.id,
        )
        db.add(doc)
        db.commit()

    # If rebid is checked, require previous_estimate_file or uploaded previous estimate
    if opportunity.rebid and not previous_estimate_file:
        # check if any previous_estimate document exists in DB for this opportunity
        pass

    save_upload(plans, 'plans')
    save_upload(addenda, 'addenda')
    save_upload(previous_estimate_file, 'previous_estimate')
    
    return RedirectResponse(url=f"/opportunities/{opportunity.id}", status_code=303)


@router.get("/{opp_id}", response_class=HTMLResponse)
async def command_center(
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
):
    """
    Opportunity Command Center - the main view for an opportunity.
    Shows all related data: estimates, activities, tasks, documents.
    """
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/opportunities/{opp_id}", status_code=303)

    today = date.today()

    # DEMO MODE: Find opportunity in demo data
    if DEMO_MODE or db is None:
        opportunities = get_all_demo_opportunities()
        opportunity = next((o for o in opportunities if o.id == opp_id), None)
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        opportunity.followup_status = get_followup_status(opportunity.next_followup, today)

        # Empty lists for demo mode
        sales_users = []
        estimators = []
        contacts = []
        gcs_accounts = []
        related_contacts = []
        quick_links = []
    else:
        opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        opportunity.followup_status = get_followup_status(opportunity.next_followup, today)

        # Get users for dropdowns
        users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
        sales_users = [u for u in users if u.role in ('Sales', 'Admin')]
        estimators = [u for u in users if u.role in ('Estimator', 'Admin')]

        # Get contacts for this account
        contacts = db.query(Contact).filter(
            Contact.account_id == opportunity.account_id
        ).order_by(Contact.last_name).all()
        # Resolve GC accounts and related contacts if present
        gcs_accounts = []
        if opportunity.gcs:
            gcs_accounts = db.query(Account).filter(Account.id.in_(opportunity.gcs)).order_by(Account.name).all()
        related_contacts = []
        if opportunity.related_contact_ids:
            related_contacts = db.query(Contact).filter(Contact.id.in_(opportunity.related_contact_ids)).order_by(Contact.last_name).all()
        quick_links = opportunity.quick_links or []
    
    return templates.TemplateResponse("opportunities/command_center.html", {
        "request": request,
        "user": user,
        "opportunity": opportunity,
        "stages": Opportunity.STAGES,
        "estimating_statuses": Opportunity.ESTIMATING_STATUSES,
        "sales_users": sales_users,
        "estimators": estimators,
        "contacts": contacts,
        "gcs_accounts": gcs_accounts,
        "related_contacts": related_contacts,
        "quick_links": quick_links,
        "today": today,
    })


@router.post("/{opp_id}/update")
async def update_opportunity(
    request: Request,
    opp_id: int,
    stage: str = Form(None),
    hdd_value: str = Form(None),
    bid_date: str = Form(None),
    owner_id: int = Form(None),
    assigned_estimator_id: int = Form(None),
    primary_contact_id: int = Form(None),
    estimating_status: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update opportunity fields."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if DEMO_MODE or db is None:
        return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Track if we need to recalculate followup
    old_stage = opportunity.stage
    old_last_contacted = opportunity.last_contacted
    old_bid_date = opportunity.bid_date
    
    # Update fields
    if stage is not None:
        opportunity.stage = stage
    # Accept hdd_value (strip commas)
    if hdd_value is not None:
        cleaned = hdd_value.replace(',', '') if hdd_value else None
        opportunity.hdd_value = Decimal(cleaned) if cleaned else None
    
    if bid_date is not None:
        opportunity.bid_date = datetime.strptime(bid_date, "%Y-%m-%d").date() if bid_date else None
    
    if owner_id is not None:
        opportunity.owner_id = owner_id if owner_id else None
    
    if assigned_estimator_id is not None:
        opportunity.assigned_estimator_id = assigned_estimator_id if assigned_estimator_id else None
    
    if primary_contact_id is not None:
        opportunity.primary_contact_id = primary_contact_id if primary_contact_id else None
    
    if estimating_status is not None:
        opportunity.estimating_status = estimating_status
    
    if notes is not None:
        opportunity.notes = notes or None
    
    # Recalculate followup if relevant fields changed
    if (old_stage != opportunity.stage or 
        old_bid_date != opportunity.bid_date or
        old_last_contacted != opportunity.last_contacted):
        update_opportunity_followup(opportunity)
    
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.post("/{opp_id}/log-contact")
async def log_contact(
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
):
    """Log a contact and update last_contacted date."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if DEMO_MODE or db is None:
        return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    opportunity.last_contacted = date.today()
    update_opportunity_followup(opportunity)
    
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.post("/{opp_id}/checklist")
async def update_checklist(
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
):
    """Update estimating checklist items."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if DEMO_MODE or db is None:
        return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Parse form data
    form_data = await request.form()
    
    if opportunity.estimating_checklist:
        for i, item in enumerate(opportunity.estimating_checklist):
            checkbox_name = f"checklist_{i}"
            item['done'] = checkbox_name in form_data
    
    # Force SQLAlchemy to see the JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(opportunity, "estimating_checklist")
    
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.get("/{opp_id}/edit", response_class=HTMLResponse)
async def edit_opportunity_form(
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
):
    """Display full edit form for opportunity."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/opportunities/{opp_id}/edit", status_code=303)

    # DEMO MODE: Show notice
    if DEMO_MODE or db is None:
        return templates.TemplateResponse("demo_mode_notice.html", {
            "request": request,
            "user": user,
            "feature": "Edit Opportunity",
            "message": "Editing opportunities is disabled in demo mode. This feature is view-only.",
            "back_url": f"/opportunities/{opp_id}",
        })

    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    accounts = db.query(Account).order_by(Account.name).all()
    scope_packages = db.query(ScopePackage).filter(
        ScopePackage.is_active == True
    ).order_by(ScopePackage.sort_order).all()

    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
    sales_users = [u for u in users if u.role in ('Sales', 'Admin')]
    estimators = [u for u in users if u.role in ('Estimator', 'Admin')]

    contacts = db.query(Contact).filter(
        Contact.account_id == opportunity.account_id
    ).order_by(Contact.last_name).all()
    
    selected_scope_ids = [s.id for s in opportunity.scopes]
    selected_scope_names = [s.name for s in opportunity.scopes]
    # Compute other/free-text scope names not in LV list for prefill
    LV_SCOPES = [
        'Horizontal Cabling (Copper)',
        'Backbone Cabling (Fiber/Copper)',
        'Site / Campus Fiber',
        'IDF / MDF Closet Buildout',
        'Security / Access Control',
        'Cameras / Surveillance',
        'Wireless / Access Points',
        'AV / Paging / Intercom',
        'Other',
    ]
    other_names = [n for n in selected_scope_names if n and n not in LV_SCOPES]
    selected_scope_other_text = ', '.join(other_names) if other_names else ''
    
    return templates.TemplateResponse("opportunities/edit.html", {
        "request": request,
        "user": user,
        "opportunity": opportunity,
        "accounts": accounts,
        "scope_packages": scope_packages,
        "sales_users": sales_users,
        "estimators": estimators,
        "contacts": contacts,
        "selected_scope_ids": selected_scope_ids,
        "selected_scope_names": selected_scope_names,
        "selected_scope_other_text": selected_scope_other_text,
        "stages": Opportunity.STAGES,
        "sources": Opportunity.SOURCES,
    })


@router.post("/{opp_id}/edit")
async def save_opportunity_edit(
    request: Request,
    opp_id: int,
    account_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(None),
    stage: str = Form(...),
    lv_value: str = Form(None),
    hdd_value: str = Form(None),
    bid_date: str = Form(None),
    bid_time: str = Form(None),
    bid_type: str = Form(None),
    submission_method: str = Form(None),
    bid_form_required: str = Form(None),
    bond_required: str = Form(None),
    prevailing_wage: str = Form(None),
    project_type: str = Form(None),
    known_risks: str = Form(None),
    rebid: str = Form(None),
    close_date: str = Form(None),
    owner_id: int = Form(None),
    assigned_estimator_id: int = Form(None),
    primary_contact_id: int = Form(None),
    source: str = Form(None),
    notes: str = Form(None),
    gc_ids: List[int] = Form(default=[]),
    related_contact_ids: List[int] = Form(default=[]),
    quick_links_text: str = Form(None),
    end_user_account_id: int = Form(None),
    last_contacted: str = Form(None),
    scope_ids: List[int] = Form(default=[]),
    scope_names: List[str] = Form(default=[]),
    scope_other_text: str = Form(None),
    db: Session = Depends(get_db)
):
    """Save full opportunity edit."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if DEMO_MODE or db is None:
        return RedirectResponse(url="/opportunities", status_code=303)
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Track for followup recalculation
    old_stage = opportunity.stage
    old_bid_date = opportunity.bid_date
    old_last_contacted = opportunity.last_contacted
    
    # Update fields
    opportunity.account_id = account_id
    opportunity.name = name
    opportunity.description = description or None
    opportunity.stage = stage
    # Parse numeric inputs (strip commas)
    def clean_num(s: Optional[str]):
        if not s:
            return None
        return s.replace(',', '')

    opportunity.lv_value = Decimal(clean_num(lv_value)) if lv_value and clean_num(lv_value) else None
    opportunity.hdd_value = Decimal(clean_num(hdd_value)) if hdd_value and clean_num(hdd_value) else None
    opportunity.bid_date = datetime.strptime(bid_date, "%Y-%m-%d").date() if bid_date else None
    if bid_time:
        try:
            opportunity.bid_time = datetime.strptime(bid_time, "%H:%M").time()
        except Exception:
            opportunity.bid_time = None
    opportunity.bid_type = bid_type or None
    opportunity.submission_method = submission_method or None
    opportunity.bid_form_required = True if bid_form_required in ('true','True','1','on') or bid_form_required == 'True' else False
    opportunity.bond_required = True if bond_required in ('true','True','1','on') or bond_required == 'True' else False
    opportunity.prevailing_wage = prevailing_wage or None
    opportunity.project_type = project_type or None
    opportunity.known_risks = known_risks or None
    opportunity.rebid = True if rebid in ('true','True','1','on') or rebid == 'True' else False
    opportunity.close_date = datetime.strptime(close_date, "%Y-%m-%d").date() if close_date else None
    opportunity.owner_id = owner_id or None
    opportunity.assigned_estimator_id = assigned_estimator_id or None
    opportunity.primary_contact_id = primary_contact_id or None
    opportunity.source = source or None
    opportunity.notes = notes or None
    # Update newly added fields
    opportunity.gcs = gc_ids or None
    opportunity.related_contact_ids = related_contact_ids or None
    opportunity.quick_links = [l.strip() for l in quick_links_text.splitlines() if l.strip()] if quick_links_text else None
    opportunity.end_user_account_id = end_user_account_id or None
    
    # Update scope packages
    db.query(OpportunityScope).filter(
        OpportunityScope.opportunity_id == opp_id
    ).delete()
    
    for scope_id in scope_ids:
        scope_link = OpportunityScope(
            opportunity_id=opp_id,
            scope_package_id=scope_id
        )
        db.add(scope_link)
    # Also handle scope names (LV scopes and Other free text)
    for sname in scope_names:
        if not sname:
            continue
        if sname == 'Other' and scope_other_text:
            sname = scope_other_text.strip()
        sp = db.query(ScopePackage).filter(ScopePackage.name == sname).first()
        if not sp:
            sp = ScopePackage(name=sname, description=None, is_active=True)
            db.add(sp)
            db.flush()
        scope_link = OpportunityScope(opportunity_id=opp_id, scope_package_id=sp.id)
        db.add(scope_link)
    
    # Parse and set last_contacted if provided
    if last_contacted is not None:
        opportunity.last_contacted = datetime.strptime(last_contacted, "%Y-%m-%d").date() if last_contacted else None

    # 'What changed' removed; only boolean rebid retained

    # Recalculate followup
    if old_stage != opportunity.stage or old_bid_date != opportunity.bid_date or old_last_contacted != opportunity.last_contacted:
        update_opportunity_followup(opportunity)
    
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.post("/{opp_id}/delete")
async def delete_opportunity(
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
):
    """Delete an opportunity."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete opportunities")
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    db.delete(opportunity)
    db.commit()
    
    return RedirectResponse(url="/opportunities", status_code=303)
