from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from typing import List, Optional, Union

from app.database import get_db
from app.models import (
    Opportunity,
    OpportunityScope,
    Account,
    Contact,
    User,
    ScopePackage,
    Activity,
    Task,
    Document,
)
from app.services.followup import calculate_next_followup, get_followup_status
from app.services.validators import (
    validate_opportunity_create,
    validate_opportunity_update,
)
from app.template_config import templates, utc_now

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


# -----------------------------
# Helpers
# -----------------------------
def update_opportunity_followup(
    opportunity: Opportunity, today: Union[date, None] = None
):
    if today is None:
        today = date.today()

    opportunity.next_followup = calculate_next_followup(
        stage=opportunity.stage,
        last_contacted=opportunity.last_contacted,
        bid_date=opportunity.bid_date,
        today=today,
    )


# -----------------------------
# List Opportunities
# -----------------------------
@router.get("", response_class=HTMLResponse)
async def list_opportunities(
    request: Request,
    search: Optional[str] = None,
    stage: Optional[str] = None,
    estimator_id: Optional[str] = None,
    stalled: Optional[str] = None,
    sort: Optional[str] = None,
    db: Session = Depends(get_db),
):
    print("SORT PARAM:", sort)  # DEBUG
    estimator_id = int(estimator_id) if estimator_id else None

    today = date.today()

    # EXPLICIT JOIN (fixes ambiguous FK error)
    # Eager load account to avoid N+1 when template accesses opp.account.name
    query = (
        db.query(Opportunity)
        .join(Account, Opportunity.account_id == Account.id)
        .options(selectinload(Opportunity.account))
    )

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Opportunity.name.ilike(term),
                Account.name.ilike(term),
            )
        )

    if stage:
        query = query.filter(Opportunity.stage == stage)

    if estimator_id:
        query = query.filter(Opportunity.assigned_estimator_id == estimator_id)

    # Filter stalled opportunities (those with a stalled_reason set)
    if stalled:
        query = query.filter(
            Opportunity.stalled_reason.isnot(None), Opportunity.stalled_reason != ""
        )

    # Apply sorting
    if sort == "value":
        query = query.order_by(
            (Opportunity.lv_value + Opportunity.hdd_value).desc().nullslast()
        )
    elif sort == "bid_date":
        query = query.order_by(Opportunity.bid_date.asc().nullslast())
    elif sort == "last_contacted":
        # "Oldest" = ASC, NULLs first (never contacted = oldest)
        query = query.order_by(Opportunity.last_contacted.asc().nullsfirst())
    elif sort == "next_followup":
        query = query.order_by(Opportunity.next_followup.asc().nullslast())
    else:
        # Default sort
        query = query.order_by(Opportunity.bid_date.asc().nullslast(), Opportunity.name)

    opportunities = query.all()

    for opp in opportunities:
        opp.followup_status = get_followup_status(opp.next_followup, today)

    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()

    return templates.TemplateResponse(
        "opportunities/list.html",
        {
            "request": request,
            "opportunities": opportunities,
            "users": users,
            "stages": Opportunity.STAGE_NAMES,
            "search": search,
            "stage": stage,
            "estimator_id": estimator_id,
            "stalled": stalled,
            "sort": sort,
        },
    )


# -----------------------------
# Intake Form
# -----------------------------
@router.get("/intake", response_class=HTMLResponse)
async def intake_form(
    request: Request, account_id: Optional[int] = None, db: Session = Depends(get_db)
):
    accounts = db.query(Account).order_by(Account.name).all()
    scope_packages = (
        db.query(ScopePackage)
        .filter(ScopePackage.is_active == True)
        .order_by(ScopePackage.sort_order)
        .all()
    )

    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()

    sales_users = [u for u in users if u.role in ("Sales", "Admin")]
    estimators = [u for u in users if u.role in ("Estimator", "Admin")]

    contacts = []
    if account_id:
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id == account_id)
            .order_by(Contact.last_name)
            .all()
        )

    return templates.TemplateResponse(
        "opportunities/intake.html",
        {
            "request": request,
            "accounts": accounts,
            "scope_packages": scope_packages,
            "sales_users": sales_users,
            "estimators": estimators,
            "contacts": contacts,
            "selected_account_id": account_id,
            "stages": Opportunity.STAGES,
            "sources": Opportunity.SOURCES,
            "error": None,
            "warnings": [],
        },
    )


# -----------------------------
# Create Opportunity
# -----------------------------
@router.post("/intake")
async def create_opportunity(
    request: Request,
    account_id: int = Form(...),
    name: str = Form(...),
    stage: str = Form("Prospecting"),
    lv_value: Optional[str] = Form(None),
    hdd_value: Optional[str] = Form(None),
    bid_date: Optional[str] = Form(None),
    bid_date_tbd: bool = Form(False),
    bid_time: Optional[str] = Form(None),
    bid_type: Optional[str] = Form(None),
    submission_method: Optional[str] = Form(None),
    bid_form_required: Optional[str] = Form(None),
    bond_required: Optional[str] = Form(None),
    prevailing_wage: Optional[str] = Form(None),
    project_type: Optional[str] = Form(None),
    rebid: bool = Form(False),
    owner_id: Optional[int] = Form(None),
    primary_contact_id: Optional[int] = Form(None),
    scope_names: List[str] = Form(default=[]),
    scope_other_text: Optional[str] = Form(None),
    gc_ids: List[str] = Form(default=[]),
    # Job Walk fields
    job_walk_required: bool = Form(False),
    job_walk_date: Optional[str] = Form(None),
    job_walk_time: Optional[str] = Form(None),
    job_walk_notes: Optional[str] = Form(None),
    # Combined job notes
    job_notes: Optional[str] = Form(None),
    # Additional details
    source: Optional[str] = Form(None),
    quick_links_text: Optional[str] = Form(None),
    related_contact_ids: List[str] = Form(default=[]),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    def clean_num(val: Optional[str]):
        return Decimal(val.replace(",", "")) if val else None

    current_user = request.state.current_user

    # Build data dict for validation
    data = {
        "account_id": account_id,
        "name": name,
        "stage": stage,
        "lv_value": lv_value,
        "hdd_value": hdd_value,
        "bid_date": bid_date,
        "bid_date_tbd": bid_date_tbd,
        "owner_id": owner_id if owner_id else current_user.id,
    }

    # Validate opportunity data
    result = validate_opportunity_create(data, db)

    # If errors, re-render form with error message
    if not result.is_valid:
        accounts = db.query(Account).order_by(Account.name).all()
        scope_packages = (
            db.query(ScopePackage)
            .filter(ScopePackage.is_active == True)
            .order_by(ScopePackage.sort_order)
            .all()
        )
        users = (
            db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
        )
        sales_users = [u for u in users if u.role in ("Sales", "Admin")]
        estimators = [u for u in users if u.role in ("Estimator", "Admin")]
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id == account_id)
            .order_by(Contact.last_name)
            .all()
            if account_id
            else []
        )

        return templates.TemplateResponse(
            "opportunities/intake.html",
            {
                "request": request,
                "accounts": accounts,
                "scope_packages": scope_packages,
                "sales_users": sales_users,
                "estimators": estimators,
                "contacts": contacts,
                "selected_account_id": account_id,
                "stages": Opportunity.STAGES,
                "sources": Opportunity.SOURCES,
                "error": "; ".join(result.errors),
                "warnings": [],
                # Preserve form values
                "form_name": name,
                "form_bid_date": bid_date,
                "form_bid_date_tbd": bid_date_tbd,
                "form_stage": stage,
                "form_owner_id": owner_id,
                "form_job_notes": job_notes,
            },
        )

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        accounts = db.query(Account).order_by(Account.name).all()
        scope_packages = (
            db.query(ScopePackage)
            .filter(ScopePackage.is_active == True)
            .order_by(ScopePackage.sort_order)
            .all()
        )
        users = (
            db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
        )
        sales_users = [u for u in users if u.role in ("Sales", "Admin")]
        estimators = [u for u in users if u.role in ("Estimator", "Admin")]
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id == account_id)
            .order_by(Contact.last_name)
            .all()
            if account_id
            else []
        )

        return templates.TemplateResponse(
            "opportunities/intake.html",
            {
                "request": request,
                "accounts": accounts,
                "scope_packages": scope_packages,
                "sales_users": sales_users,
                "estimators": estimators,
                "contacts": contacts,
                "selected_account_id": account_id,
                "stages": Opportunity.STAGES,
                "sources": Opportunity.SOURCES,
                "error": None,
                "warnings": result.warnings,
                # Preserve form values
                "form_name": name,
                "form_bid_date": bid_date,
                "form_bid_date_tbd": bid_date_tbd,
                "form_stage": stage,
                "form_owner_id": owner_id,
                "form_job_notes": job_notes,
            },
        )

    # Parse quick links from text (one per line)
    parsed_quick_links = None
    if quick_links_text:
        parsed_quick_links = [
            line.strip() for line in quick_links_text.strip().split("\n") if line.strip()
        ]

    # Parse related contact IDs
    parsed_related_contact_ids = None
    if related_contact_ids:
        parsed_related_contact_ids = [int(cid) for cid in related_contact_ids if cid]

    opportunity = Opportunity(
        account_id=account_id,
        name=name,
        stage=stage,
        probability=Opportunity.STAGE_PROBABILITIES.get(stage, 0),
        lv_value=clean_num(lv_value),
        hdd_value=clean_num(hdd_value),
        bid_date=datetime.strptime(bid_date, "%Y-%m-%d").date() if bid_date else None,
        bid_time=datetime.strptime(bid_time, "%H:%M").time() if bid_time else None,
        bid_type=bid_type or None,
        submission_method=submission_method or None,
        bid_form_required=bid_form_required == "true" if bid_form_required else False,
        bond_required=bond_required == "true" if bond_required else False,
        prevailing_wage=prevailing_wage or None,
        project_type=project_type or None,
        rebid=rebid,
        owner_id=owner_id if owner_id else current_user.id,
        primary_contact_id=primary_contact_id or None,
        last_contacted=date.today(),
        gcs=[int(gc_id) for gc_id in gc_ids if gc_id] if gc_ids else None,
        # Job Walk fields
        job_walk_required=job_walk_required,
        job_walk_date=datetime.strptime(job_walk_date, "%Y-%m-%d").date() if job_walk_date else None,
        job_walk_time=datetime.strptime(job_walk_time, "%H:%M").time() if job_walk_time else None,
        job_walk_notes=job_walk_notes or None,
        # Combined job notes
        job_notes=job_notes or None,
        # Additional details
        source=source or None,
        quick_links=parsed_quick_links,
        related_contact_ids=parsed_related_contact_ids,
    )

    update_opportunity_followup(opportunity)

    db.add(opportunity)
    db.flush()  # Get the opportunity.id

    # Add scope packages
    for scope_name in scope_names:
        if scope_name == "Other" and scope_other_text:
            # Use the custom text instead of "Other"
            scope_pkg = (
                db.query(ScopePackage)
                .filter(ScopePackage.name == scope_other_text)
                .first()
            )
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_other_text, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(
                OpportunityScope(
                    opportunity_id=opportunity.id, scope_package_id=scope_pkg.id
                )
            )
        else:
            scope_pkg = (
                db.query(ScopePackage).filter(ScopePackage.name == scope_name).first()
            )
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_name, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(
                OpportunityScope(
                    opportunity_id=opportunity.id, scope_package_id=scope_pkg.id
                )
            )

    db.commit()

    return RedirectResponse(url=f"/opportunities/{opportunity.id}", status_code=303)


# -----------------------------
# Opportunity Detail
# -----------------------------
@router.get("/{opp_id}", response_class=HTMLResponse)
async def opportunity_detail(
    request: Request, opp_id: int, db: Session = Depends(get_db)
):
    today = date.today()

    # Eager load all relationships accessed in command_center.html template:
    # - account (name, id)
    # - primary_contact (full_name, title, email, phone)
    # - tasks (list) with task.assigned_to
    # - activities (list) with activity.contact
    # - owner (full_name)
    # - assigned_estimator (full_name)
    # - scopes via scope_links
    opportunity = (
        db.query(Opportunity)
        .options(
            selectinload(Opportunity.account),
            selectinload(Opportunity.primary_contact),
            selectinload(Opportunity.tasks).selectinload(Task.assigned_to),
            selectinload(Opportunity.activities).selectinload(Activity.contact),
            selectinload(Opportunity.owner),
            selectinload(Opportunity.assigned_estimator),
            selectinload(Opportunity.scope_links).selectinload(
                OpportunityScope.scope_package
            ),
        )
        .filter(Opportunity.id == opp_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opportunity.followup_status = get_followup_status(opportunity.next_followup, today)

    # Query contacts for this opportunity's account
    contacts = (
        db.query(Contact)
        .filter(Contact.account_id == opportunity.account_id)
        .order_by(Contact.last_name)
        .all()
    )

    # Query estimators for task assignment dropdown
    estimators = (
        db.query(User)
        .filter(User.is_active == True, User.role.in_(["Estimator", "Admin"]))
        .order_by(User.full_name)
        .all()
    )

    # Load GC accounts if opportunity has GCs
    gcs_accounts = []
    if opportunity.gcs:
        gcs_accounts = db.query(Account).filter(Account.id.in_(opportunity.gcs)).all()

    # Load related contacts if opportunity has related_contact_ids
    related_contacts = []
    if opportunity.related_contact_ids:
        related_contacts = (
            db.query(Contact)
            .filter(Contact.id.in_(opportunity.related_contact_ids))
            .all()
        )

    # Load quick links
    quick_links = opportunity.quick_links or []

    return templates.TemplateResponse(
        "opportunities/command_center.html",
        {
            "request": request,
            "opportunity": opportunity,
            "today": today,
            "contacts": contacts,
            "estimators": estimators,
            "gcs_accounts": gcs_accounts,
            "related_contacts": related_contacts,
            "quick_links": quick_links,
        },
    )


# -----------------------------
# Delete Opportunity
# -----------------------------
@router.post("/{opp_id}/delete")
async def delete_opportunity(opp_id: int, db: Session = Depends(get_db)):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Explicitly delete children first (don't rely on cascade)
    db.query(Activity).filter(Activity.opportunity_id == opp_id).delete()
    db.query(Task).filter(Task.opportunity_id == opp_id).delete()
    db.query(OpportunityScope).filter(
        OpportunityScope.opportunity_id == opp_id
    ).delete()
    db.query(Document).filter(Document.opportunity_id == opp_id).delete()

    db.delete(opportunity)
    db.commit()

    return RedirectResponse("/opportunities", status_code=303)


# -----------------------------
# Quick Stage Update
# -----------------------------
@router.post("/{opp_id}/update-stage")
async def update_stage(
    request: Request, opp_id: int, stage: str = Form(...), db: Session = Depends(get_db)
):
    """Quick update opportunity stage without full edit form."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    old_stage = opportunity.stage

    opportunity.stage = stage
    opportunity.probability = Opportunity.STAGE_PROBABILITIES.get(stage, 0)
    opportunity.last_contacted = date.today()
    update_opportunity_followup(opportunity)

    # Log stage change as activity for pipeline tracking
    current_user = request.state.current_user
    if old_stage != stage:
        activity = Activity(
            opportunity_id=opp_id,
            activity_type="note",
            subject=f"Stage changed: {old_stage} → {stage}",
            description=f"Pipeline stage updated from {old_stage} to {stage}",
            activity_date=utc_now(),
            created_by_id=current_user.id,
        )
        db.add(activity)

    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


# -----------------------------
# Log Contact (Quick Action)
# -----------------------------
@router.post("/{opp_id}/log-contact")
async def log_contact(opp_id: int, db: Session = Depends(get_db)):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opportunity.last_contacted = date.today()
    update_opportunity_followup(opportunity)
    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


# -----------------------------
# Edit Opportunity
# -----------------------------
@router.get("/{opp_id}/edit", response_class=HTMLResponse)
async def edit_opportunity_form(
    request: Request, opp_id: int, db: Session = Depends(get_db)
):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    accounts = db.query(Account).order_by(Account.name).all()
    contacts = (
        db.query(Contact)
        .filter(Contact.account_id == opportunity.account_id)
        .order_by(Contact.last_name)
        .all()
    )

    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()

    sales_users = [u for u in users if u.role in ("Sales", "Admin")]
    estimators = [u for u in users if u.role in ("Estimator", "Admin")]

    selected_scope_names = (
        [s.name for s in opportunity.scopes] if opportunity.scopes else []
    )
    selected_scope_other_text = ""
    for s in opportunity.scopes or []:
        if s.name not in [
            "Horizontal Cabling (Copper)",
            "Backbone Cabling (Fiber/Copper)",
            "Site / Campus Fiber",
            "IDF / MDF Closet Buildout",
            "Security / Access Control",
            "Cameras / Surveillance",
            "Wireless / Access Points",
            "AV / Paging / Intercom",
            "Other",
        ]:
            selected_scope_other_text = s.name

    return templates.TemplateResponse(
        "opportunities/edit.html",
        {
            "request": request,
            "opportunity": opportunity,
            "accounts": accounts,
            "contacts": contacts,
            "sales_users": sales_users,
            "estimators": estimators,
            "stages": Opportunity.STAGES,
            "sources": Opportunity.SOURCES,
            "stalled_reasons": Opportunity.STALLED_REASONS,
            "selected_scope_names": selected_scope_names,
            "selected_scope_other_text": selected_scope_other_text,
            "error": None,
            "warnings": [],
        },
    )


@router.post("/{opp_id}/edit")
async def update_opportunity(
    request: Request,
    opp_id: int,
    account_id: int = Form(...),
    name: str = Form(...),
    stage: str = Form("Prospecting"),
    description: str = Form(None),
    lv_value: str = Form(None),
    hdd_value: str = Form(None),
    bid_date: str = Form(None),
    bid_date_tbd: bool = Form(False),
    bid_time: str = Form(None),
    owner_id: int = Form(None),
    assigned_estimator_id: int = Form(None),
    primary_contact_id: int = Form(None),
    source: str = Form(None),
    notes: str = Form(None),
    bid_type: str = Form(None),
    submission_method: str = Form(None),
    bid_form_required: str = Form(None),
    bond_required: str = Form(None),
    prevailing_wage: str = Form(None),
    project_type: str = Form(None),
    rebid: str = Form(None),
    known_risks: str = Form(None),
    stalled_reason: str = Form(None),
    last_contacted: str = Form(None),
    quick_links_text: str = Form(None),
    end_user_account_id: int = Form(None),
    gc_ids: List[str] = Form(default=[]),
    scope_names: List[str] = Form(default=[]),
    scope_other_text: Optional[str] = Form(None),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    def clean_num(val):
        if not val:
            return None
        return Decimal(str(val).replace(",", ""))

    # Capture old stage for activity logging and validation
    old_stage = opportunity.stage
    current_user = request.state.current_user

    # Build data dict for validation
    data = {
        "account_id": account_id,
        "name": name,
        "stage": stage,
        "lv_value": lv_value,
        "hdd_value": hdd_value,
        "bid_date": bid_date,
        "bid_date_tbd": bid_date_tbd,
        "owner_id": owner_id if owner_id else current_user.id,
    }

    # Validate opportunity data
    result = validate_opportunity_update(
        data, db, existing_id=opp_id, old_stage=old_stage
    )

    # If errors, re-render form with error message
    if not result.is_valid:
        accounts = db.query(Account).order_by(Account.name).all()
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id == opportunity.account_id)
            .order_by(Contact.last_name)
            .all()
        )
        users = (
            db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
        )
        sales_users = [u for u in users if u.role in ("Sales", "Admin")]
        estimators = [u for u in users if u.role in ("Estimator", "Admin")]
        selected_scope_names = (
            [s.name for s in opportunity.scopes] if opportunity.scopes else []
        )

        return templates.TemplateResponse(
            "opportunities/edit.html",
            {
                "request": request,
                "opportunity": opportunity,
                "accounts": accounts,
                "contacts": contacts,
                "sales_users": sales_users,
                "estimators": estimators,
                "stages": Opportunity.STAGES,
                "sources": Opportunity.SOURCES,
                "stalled_reasons": Opportunity.STALLED_REASONS,
                "selected_scope_names": selected_scope_names,
                "selected_scope_other_text": scope_other_text or "",
                "error": "; ".join(result.errors),
                "warnings": [],
            },
        )

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        accounts = db.query(Account).order_by(Account.name).all()
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id == opportunity.account_id)
            .order_by(Contact.last_name)
            .all()
        )
        users = (
            db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
        )
        sales_users = [u for u in users if u.role in ("Sales", "Admin")]
        estimators = [u for u in users if u.role in ("Estimator", "Admin")]
        selected_scope_names = (
            [s.name for s in opportunity.scopes] if opportunity.scopes else []
        )

        return templates.TemplateResponse(
            "opportunities/edit.html",
            {
                "request": request,
                "opportunity": opportunity,
                "accounts": accounts,
                "contacts": contacts,
                "sales_users": sales_users,
                "estimators": estimators,
                "stages": Opportunity.STAGES,
                "sources": Opportunity.SOURCES,
                "stalled_reasons": Opportunity.STALLED_REASONS,
                "selected_scope_names": selected_scope_names,
                "selected_scope_other_text": scope_other_text or "",
                "error": None,
                "warnings": result.warnings,
            },
        )

    opportunity.account_id = account_id
    opportunity.name = name
    opportunity.stage = stage
    opportunity.probability = Opportunity.STAGE_PROBABILITIES.get(stage, 0)
    opportunity.description = description or None
    opportunity.lv_value = clean_num(lv_value)
    opportunity.hdd_value = clean_num(hdd_value)
    opportunity.bid_date = (
        datetime.strptime(bid_date, "%Y-%m-%d").date() if bid_date else None
    )
    opportunity.bid_time = (
        datetime.strptime(bid_time, "%H:%M").time() if bid_time else None
    )
    opportunity.owner_id = (
        owner_id if owner_id else current_user.id
    )  # Enforce ownership
    opportunity.assigned_estimator_id = assigned_estimator_id or None
    opportunity.primary_contact_id = primary_contact_id or None
    opportunity.source = source or None
    opportunity.notes = notes or None
    opportunity.bid_type = bid_type or None
    opportunity.submission_method = submission_method or None
    opportunity.bid_form_required = (
        bid_form_required == "true" if bid_form_required else None
    )
    opportunity.bond_required = bond_required == "true" if bond_required else None
    opportunity.prevailing_wage = prevailing_wage or None
    opportunity.project_type = project_type or None
    opportunity.rebid = rebid == "true" if rebid else False
    opportunity.known_risks = known_risks or None
    opportunity.stalled_reason = stalled_reason or None
    opportunity.end_user_account_id = end_user_account_id or None

    if last_contacted:
        opportunity.last_contacted = datetime.strptime(
            last_contacted, "%Y-%m-%d"
        ).date()

    if quick_links_text:
        opportunity.quick_links = [
            link.strip()
            for link in quick_links_text.strip().split("\n")
            if link.strip()
        ]
    else:
        opportunity.quick_links = None

    # Update GCs list
    if gc_ids:
        opportunity.gcs = [int(gc_id) for gc_id in gc_ids if gc_id]
    else:
        opportunity.gcs = None

    # Update scope packages - clear existing and re-add
    db.query(OpportunityScope).filter(
        OpportunityScope.opportunity_id == opp_id
    ).delete()

    for scope_name in scope_names:
        if scope_name == "Other" and scope_other_text:
            scope_pkg = (
                db.query(ScopePackage)
                .filter(ScopePackage.name == scope_other_text)
                .first()
            )
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_other_text, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(
                OpportunityScope(opportunity_id=opp_id, scope_package_id=scope_pkg.id)
            )
        else:
            scope_pkg = (
                db.query(ScopePackage).filter(ScopePackage.name == scope_name).first()
            )
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_name, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(
                OpportunityScope(opportunity_id=opp_id, scope_package_id=scope_pkg.id)
            )

    update_opportunity_followup(opportunity)

    # Log stage change as activity for pipeline tracking
    if old_stage != stage:
        activity = Activity(
            opportunity_id=opp_id,
            activity_type="note",
            subject=f"Stage changed: {old_stage} → {stage}",
            description=f"Pipeline stage updated from {old_stage} to {stage}",
            activity_date=utc_now(),
            created_by_id=current_user.id,
        )
        db.add(activity)

    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


# -----------------------------
# Calendar View
# -----------------------------
@router.get("/calendar/view", response_class=HTMLResponse)
async def calendar_view(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "opportunities/calendar.html", {"request": request}
    )


@router.get("/calendar/events")
async def calendar_events(db: Session = Depends(get_db)):
    opportunities = (
        db.query(Opportunity)
        .filter(Opportunity.bid_date.isnot(None))
        .filter(Opportunity.stage.notin_(["Won", "Lost"]))
        .all()
    )

    events = []
    for opp in opportunities:
        events.append(
            {
                "id": opp.id,
                "title": opp.name,
                "start": opp.bid_date.isoformat(),
                "url": f"/opportunities/{opp.id}",
                "backgroundColor": "#0d6efd",
                "borderColor": "#0d6efd",
            }
        )

    return JSONResponse(content=events)


# -----------------------------
# Auto-Save API
# -----------------------------
from pydantic import BaseModel, field_validator
from typing import Any, Union


def parse_bool_field(v: Any) -> Optional[bool]:
    """Parse boolean from string/bool/None."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    return bool(v)


def parse_int_list(v: Any) -> Optional[List[int]]:
    """Parse list of integers from strings or ints."""
    if v is None:
        return None
    if not isinstance(v, list):
        return None
    result = []
    for item in v:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str) and item.strip():
            try:
                result.append(int(item))
            except ValueError:
                pass
    return result if result else None


def parse_int_field(v: Any) -> Optional[int]:
    """Parse integer from string/int/None."""
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return None
    return None


class OpportunityAutoSaveRequest(BaseModel):
    # Core fields
    name: Optional[str] = None
    account_id: Optional[Union[int, str]] = None
    stage: Optional[str] = None
    description: Optional[str] = None
    lv_value: Optional[str] = None
    hdd_value: Optional[str] = None
    primary_contact_id: Optional[Union[int, str]] = None
    end_user_account_id: Optional[Union[int, str]] = None
    # Dates
    bid_date: Optional[str] = None
    bid_date_tbd: Optional[Union[bool, str]] = None
    bid_time: Optional[str] = None
    last_contacted: Optional[str] = None
    # Assignment
    owner_id: Optional[Union[int, str]] = None
    assigned_estimator_id: Optional[Union[int, str]] = None
    # Bid details
    source: Optional[str] = None
    notes: Optional[str] = None
    bid_type: Optional[str] = None
    submission_method: Optional[str] = None
    bid_form_required: Optional[Union[bool, str]] = None
    bond_required: Optional[Union[bool, str]] = None
    prevailing_wage: Optional[str] = None
    project_type: Optional[str] = None
    rebid: Optional[Union[bool, str]] = None
    known_risks: Optional[str] = None
    stalled_reason: Optional[str] = None
    quick_links_text: Optional[str] = None
    # Related entities - accept strings or ints
    gc_ids: Optional[List[Union[int, str]]] = None
    scope_names: Optional[List[str]] = None
    scope_other_text: Optional[str] = None
    related_contact_ids: Optional[List[Union[int, str]]] = None
    # Hidden field from form (ignored)
    confirm_warnings: Optional[Union[bool, str]] = None

    class Config:
        extra = "ignore"  # Ignore unknown fields


@router.post("/{opp_id}/auto-save")
async def auto_save_opportunity(
    opp_id: int,
    request: Request,
    data: OpportunityAutoSaveRequest,
    db: Session = Depends(get_db),
):
    """Auto-save opportunity fields (JSON API for real-time updates)."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    current_user = request.state.current_user
    old_stage = opportunity.stage

    def clean_num(val):
        if not val:
            return None
        return Decimal(str(val).replace(",", ""))

    # Core fields
    if data.name is not None:
        opportunity.name = data.name
    if data.account_id is not None:
        opportunity.account_id = parse_int_field(data.account_id)
    if data.stage is not None:
        opportunity.stage = data.stage
    if data.description is not None:
        opportunity.description = data.description or None
    if data.lv_value is not None:
        opportunity.lv_value = clean_num(data.lv_value)
    if data.hdd_value is not None:
        opportunity.hdd_value = clean_num(data.hdd_value)
    if data.primary_contact_id is not None:
        opportunity.primary_contact_id = parse_int_field(data.primary_contact_id)
    if data.end_user_account_id is not None:
        opportunity.end_user_account_id = parse_int_field(data.end_user_account_id)

    # Dates
    if data.bid_date is not None:
        if data.bid_date.strip():
            opportunity.bid_date = datetime.strptime(data.bid_date, "%Y-%m-%d").date()
        else:
            opportunity.bid_date = None
    if data.bid_date_tbd is not None:
        opportunity.bid_date_tbd = parse_bool_field(data.bid_date_tbd)
    if data.bid_time is not None:
        if data.bid_time.strip():
            opportunity.bid_time = datetime.strptime(data.bid_time, "%H:%M").time()
        else:
            opportunity.bid_time = None
    if data.last_contacted is not None:
        if data.last_contacted.strip():
            opportunity.last_contacted = datetime.strptime(data.last_contacted, "%Y-%m-%d").date()
        else:
            opportunity.last_contacted = None

    # Assignment
    if data.owner_id is not None:
        opportunity.owner_id = parse_int_field(data.owner_id)
    if data.assigned_estimator_id is not None:
        opportunity.assigned_estimator_id = parse_int_field(data.assigned_estimator_id)

    # Bid details
    if data.source is not None:
        opportunity.source = data.source or None
    if data.notes is not None:
        opportunity.notes = data.notes or None
    if data.bid_type is not None:
        opportunity.bid_type = data.bid_type or None
    if data.submission_method is not None:
        opportunity.submission_method = data.submission_method or None
    if data.bid_form_required is not None:
        opportunity.bid_form_required = parse_bool_field(data.bid_form_required)
    if data.bond_required is not None:
        opportunity.bond_required = parse_bool_field(data.bond_required)
    if data.prevailing_wage is not None:
        opportunity.prevailing_wage = data.prevailing_wage or None
    if data.project_type is not None:
        opportunity.project_type = data.project_type or None
    if data.rebid is not None:
        opportunity.rebid = parse_bool_field(data.rebid)
    if data.known_risks is not None:
        opportunity.known_risks = data.known_risks or None
    if data.stalled_reason is not None:
        opportunity.stalled_reason = data.stalled_reason or None

    # Quick links
    if data.quick_links_text is not None:
        if data.quick_links_text.strip():
            opportunity.quick_links = [
                ln.strip() for ln in data.quick_links_text.strip().splitlines() if ln.strip()
            ]
        else:
            opportunity.quick_links = None

    # GC accounts (JSON array)
    if data.gc_ids is not None:
        opportunity.gcs = parse_int_list(data.gc_ids)

    # Related contacts
    if data.related_contact_ids is not None:
        opportunity.related_contact_ids = parse_int_list(data.related_contact_ids)

    # Scopes
    if data.scope_names is not None:
        # Clear existing scopes and rebuild
        db.query(OpportunityScope).filter(OpportunityScope.opportunity_id == opp_id).delete()
        for scope_name in data.scope_names:
            scope_pkg = db.query(ScopePackage).filter(ScopePackage.name == scope_name).first()
            if scope_pkg:
                opp_scope = OpportunityScope(
                    opportunity_id=opp_id,
                    scope_package_id=scope_pkg.id,
                    name=scope_name,
                    description=data.scope_other_text if scope_name == "Other" else None,
                )
                db.add(opp_scope)

    # Update follow-up based on new state
    update_opportunity_followup(opportunity)

    # Log stage change if applicable
    if old_stage != opportunity.stage:
        activity = Activity(
            opportunity_id=opp_id,
            activity_type="note",
            subject=f"Stage changed: {old_stage} → {opportunity.stage}",
            description=f"Pipeline stage updated from {old_stage} to {opportunity.stage}",
            activity_date=utc_now(),
            created_by_id=current_user.id,
        )
        db.add(activity)

    db.commit()

    return {"ok": True, "id": opportunity.id}
