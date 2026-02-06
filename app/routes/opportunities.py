from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from typing import List, Optional, Union
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    Opportunity,
    OpportunityScope,
    OpportunityAccount,
    Account,
    Contact,
    User,
    ScopePackage,
    Activity,
    Task,
    UserSummarySuppression,
)
from app.services.followup import calculate_next_followup, get_followup_status
from app.services.validators import (
    validate_opportunity_create,
    validate_opportunity_update,
)
from app.template_config import templates, utc_now
from app.utils.safe_redirect import safe_redirect_url

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


def sync_opportunity_accounts(
    db: Session, opportunity_id: int, account_ids: List[int], primary_account_id: int
):
    """Sync the opportunity_accounts junction table."""
    # Delete existing links
    db.query(OpportunityAccount).filter(
        OpportunityAccount.opportunity_id == opportunity_id
    ).delete()

    # Add new links
    for account_id in account_ids:
        link = OpportunityAccount(
            opportunity_id=opportunity_id,
            account_id=account_id,
        )
        db.add(link)

    # Update primary_account_id on opportunity
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if opp:
        opp.primary_account_id = primary_account_id


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
    estimator_id = int(estimator_id) if estimator_id else None

    today = date.today()

    # Query opportunities with eager loading
    query = (
        db.query(Opportunity)
        .options(
            selectinload(Opportunity.primary_account),
            selectinload(Opportunity.account_links).selectinload(OpportunityAccount.account),
        )
    )

    if search:
        term = f"%{search}%"
        # Search in opportunity name or linked account names
        query = query.outerjoin(OpportunityAccount).outerjoin(
            Account, OpportunityAccount.account_id == Account.id
        ).filter(
            or_(
                Opportunity.name.ilike(term),
                Account.name.ilike(term),
            )
        ).distinct()

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
        query = query.order_by(Opportunity.last_contacted.asc().nullsfirst())
    elif sort == "next_followup":
        query = query.order_by(Opportunity.next_followup.asc().nullslast())
    else:
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
            "selected_account_ids": [account_id] if account_id else [],
            "selected_primary_account_id": account_id,
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
    name: str = Form(...),
    account_ids: List[str] = Form(default=[]),
    primary_account_id: Optional[int] = Form(None),
    stage: str = Form("Prospecting"),
    lv_value: Optional[str] = Form(None),
    hdd_value: Optional[str] = Form(None),
    bid_date: Optional[str] = Form(None),
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
    end_user_account_id: Optional[int] = Form(None),
    job_walk_required: bool = Form(False),
    job_walk_date: Optional[str] = Form(None),
    job_walk_time: Optional[str] = Form(None),
    job_walk_notes: Optional[str] = Form(None),
    job_notes: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    quick_links_text: Optional[str] = Form(None),
    related_contact_ids: List[str] = Form(default=[]),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    def clean_num(val: Optional[str]):
        if not val:
            return None
        try:
            return Decimal(str(val).strip().replace(",", "").replace("$", ""))
        except (InvalidOperation, ValueError):
            return None

    current_user = request.state.current_user

    # Parse account IDs
    parsed_account_ids = [int(aid) for aid in account_ids if aid]

    # Set primary account to first if not specified
    if not primary_account_id and parsed_account_ids:
        primary_account_id = parsed_account_ids[0]

    # Build data dict for validation
    data = {
        "account_ids": parsed_account_ids,
        "primary_account_id": primary_account_id,
        "primary_contact_id": primary_contact_id,
        "name": name,
        "stage": stage,
        "lv_value": lv_value,
        "hdd_value": hdd_value,
        "bid_date": bid_date,
                "owner_id": owner_id if owner_id else current_user.id,
    }

    # Validate opportunity data
    result = validate_opportunity_create(data, db)

    # Helper to re-render form
    def render_form_with_error(error_msg=None, warnings_list=None):
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
        contacts = []

        return templates.TemplateResponse(
            "opportunities/intake.html",
            {
                "request": request,
                "accounts": accounts,
                "scope_packages": scope_packages,
                "sales_users": sales_users,
                "estimators": estimators,
                "contacts": contacts,
                "selected_account_ids": parsed_account_ids,
                "selected_primary_account_id": primary_account_id,
                "selected_end_user_id": end_user_account_id,
                "stages": Opportunity.STAGES,
                "sources": Opportunity.SOURCES,
                "error": error_msg,
                "warnings": warnings_list or [],
                "form_name": name,
                "form_bid_date": bid_date,
                                "form_stage": stage,
                "form_owner_id": owner_id,
                "form_job_notes": job_notes,
            },
        )

    # If errors, re-render form with error message
    if not result.is_valid:
        return render_form_with_error("; ".join(result.errors))

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        return render_form_with_error(None, result.warnings)

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
        primary_account_id=primary_account_id,
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
        end_user_account_id=end_user_account_id or None,
        job_walk_required=job_walk_required,
        job_walk_date=datetime.strptime(job_walk_date, "%Y-%m-%d").date() if job_walk_date else None,
        job_walk_time=datetime.strptime(job_walk_time, "%H:%M").time() if job_walk_time else None,
        job_walk_notes=job_walk_notes or None,
        job_notes=job_notes or None,
        source=source or None,
        quick_links=parsed_quick_links,
        related_contact_ids=parsed_related_contact_ids,
    )

    update_opportunity_followup(opportunity)

    db.add(opportunity)
    db.flush()  # Get the opportunity.id

    # Add account links
    for account_id in parsed_account_ids:
        link = OpportunityAccount(
            opportunity_id=opportunity.id,
            account_id=account_id,
        )
        db.add(link)

    # Add scope packages
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
                OpportunityScope(
                    opportunity_id=opportunity.id, scope_package_id=scope_pkg.id
                )
            )
        else:
            scope_pkg = (
                db.query(ScopePackage).filter(ScopePackage.name == scope_name).first()
            )
            if scope_pkg:
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

    opportunity = (
        db.query(Opportunity)
        .options(
            selectinload(Opportunity.primary_account),
            selectinload(Opportunity.account_links).selectinload(OpportunityAccount.account),
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

    # Get all account IDs for this opportunity
    opp_account_ids = opportunity.account_ids

    # Query contacts for all linked accounts
    contacts = []
    if opp_account_ids:
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id.in_(opp_account_ids))
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
    db.query(OpportunityAccount).filter(
        OpportunityAccount.opportunity_id == opp_id
    ).delete()
    db.query(UserSummarySuppression).filter(
        UserSummarySuppression.opportunity_id == opp_id
    ).delete()

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
# Push Follow-up (Quick Action)
# -----------------------------
@router.post("/{opp_id}/push-followup")
async def push_followup(request: Request, opp_id: int, db: Session = Depends(get_db)):
    """Push the next follow-up date by 7 days from today.

    This allows users to manually defer follow-up when no action is required.
    """
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Push follow-up to 7 days from today
    opportunity.next_followup = date.today() + timedelta(days=7)
    db.commit()

    # Redirect back to where we came from (Dashboard by default)
    redirect_to = safe_redirect_url(request.query_params.get("from"), "/")
    return RedirectResponse(url=redirect_to, status_code=303)


# -----------------------------
# Edit Opportunity
# -----------------------------
@router.get("/{opp_id}/edit", response_class=HTMLResponse)
async def edit_opportunity_form(
    request: Request, opp_id: int, db: Session = Depends(get_db)
):
    opportunity = (
        db.query(Opportunity)
        .options(
            selectinload(Opportunity.account_links).selectinload(OpportunityAccount.account),
            selectinload(Opportunity.scope_links).selectinload(OpportunityScope.scope_package),
        )
        .filter(Opportunity.id == opp_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    accounts = db.query(Account).order_by(Account.name).all()

    # Get contacts for all linked accounts
    opp_account_ids = opportunity.account_ids
    contacts = []
    if opp_account_ids:
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id.in_(opp_account_ids))
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
    standard_scopes = [
        "Horizontal Cabling (Copper)",
        "Backbone Cabling (Fiber/Copper)",
        "Site / Campus Fiber",
        "IDF / MDF Closet Buildout",
        "Security / Access Control",
        "Cameras / Surveillance",
        "Wireless / Access Points",
        "AV / Paging / Intercom",
        "Other",
    ]
    for s in opportunity.scopes or []:
        if s.name not in standard_scopes:
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
    name: str = Form(...),
    account_ids: List[str] = Form(default=[]),
    primary_account_id: Optional[int] = Form(None),
    stage: str = Form("Prospecting"),
    description: str = Form(None),
    lv_value: str = Form(None),
    hdd_value: str = Form(None),
    bid_date: str = Form(None),
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
    scope_names: List[str] = Form(default=[]),
    scope_other_text: Optional[str] = Form(None),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    opportunity = (
        db.query(Opportunity)
        .options(selectinload(Opportunity.account_links))
        .filter(Opportunity.id == opp_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    def clean_num(val):
        if not val:
            return None
        try:
            return Decimal(str(val).strip().replace(",", "").replace("$", ""))
        except (InvalidOperation, ValueError):
            return None

    # Parse account IDs
    parsed_account_ids = [int(aid) for aid in account_ids if aid]

    # Set primary account to first if not specified
    if not primary_account_id and parsed_account_ids:
        primary_account_id = parsed_account_ids[0]

    # Capture old stage for activity logging and validation
    old_stage = opportunity.stage
    current_user = request.state.current_user

    # Build data dict for validation
    data = {
        "account_ids": parsed_account_ids,
        "primary_account_id": primary_account_id,
        "primary_contact_id": primary_contact_id,
        "name": name,
        "stage": stage,
        "lv_value": lv_value,
        "hdd_value": hdd_value,
        "bid_date": bid_date,
                "owner_id": owner_id if owner_id else current_user.id,
    }

    # Validate opportunity data
    result = validate_opportunity_update(
        data, db, existing_id=opp_id, old_stage=old_stage
    )

    # Helper to re-render form
    def render_form_with_error(error_msg=None, warnings_list=None):
        accounts = db.query(Account).order_by(Account.name).all()
        opp_account_ids = opportunity.account_ids
        contacts = []
        if opp_account_ids:
            contacts = (
                db.query(Contact)
                .filter(Contact.account_id.in_(opp_account_ids))
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
                "error": error_msg,
                "warnings": warnings_list or [],
            },
        )

    # If errors, re-render form with error message
    if not result.is_valid:
        return render_form_with_error("; ".join(result.errors))

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        return render_form_with_error(None, result.warnings)

    # Update opportunity fields
    opportunity.primary_account_id = primary_account_id
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
    opportunity.owner_id = owner_id if owner_id else current_user.id
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

    # Sync account links
    sync_opportunity_accounts(db, opp_id, parsed_account_ids, primary_account_id)

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
            if scope_pkg:
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

# Column names for Opportunity model (only these can be set)
OPPORTUNITY_COLUMNS = {
    "name", "description", "stage", "probability", "bid_date", "close_date",
    "last_contacted", "next_followup", "bid_type", "submission_method", "bid_time",
    "bid_form_required", "bond_required", "prevailing_wage", "known_risks",
    "project_type", "rebid", "lv_value", "hdd_value", "owner_id",
    "assigned_estimator_id", "estimating_status", "estimating_checklist",
    "primary_contact_id", "source", "notes", "related_contact_ids", "quick_links",
    "end_user_account_id", "stalled_reason", "job_walk_required", "job_walk_date",
    "job_walk_time", "job_walk_notes", "job_notes", "primary_account_id", "account_id",
}


@router.post("/{opp_id}/auto-save")
async def auto_save_opportunity(
    opp_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Production-safe autosave. Never raises 422 or 500."""
    try:
        opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
        if not opportunity:
            return {"status": "saved"}

        try:
            payload = await request.json()
        except Exception:
            try:
                form = await request.form()
                payload = dict(form)
            except Exception:
                payload = {}

        old_stage = opportunity.stage

        def clean_decimal(v):
            if v in (None, "", "null"):
                return None
            try:
                return Decimal(str(v).replace(",", ""))
            except Exception:
                return None

        def clean_int(v):
            if v in (None, "", "null"):
                return None
            try:
                return int(v)
            except Exception:
                return None

        def clean_bool(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.lower() in ("true", "1", "yes", "on")
            return False

        def clean_date(v):
            if not v or v in ("", "null"):
                return None
            if isinstance(v, date):
                return v
            try:
                return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()
            except Exception:
                return None

        def clean_time(v):
            if not v or v in ("", "null"):
                return None
            try:
                return datetime.strptime(str(v).strip(), "%H:%M").time()
            except Exception:
                return None

        # Field updates - only actual columns
        for field, value in payload.items():
            if field not in OPPORTUNITY_COLUMNS:
                continue

            try:
                if field in ("lv_value", "hdd_value"):
                    setattr(opportunity, field, clean_decimal(value))
                elif field.endswith("_id") and field != "related_contact_ids":
                    setattr(opportunity, field, clean_int(value))
                elif field in ("bid_form_required", "bond_required", "rebid", "job_walk_required"):
                    setattr(opportunity, field, clean_bool(value))
                elif field.endswith("_date"):
                    setattr(opportunity, field, clean_date(value))
                elif field.endswith("_time"):
                    setattr(opportunity, field, clean_time(value))
                elif field == "probability":
                    setattr(opportunity, field, clean_int(value))
                else:
                    if isinstance(value, str):
                        setattr(opportunity, field, value.strip() if value.strip() else None)
                    else:
                        setattr(opportunity, field, value if value else None)
            except Exception:
                continue

        # Handle quick_links_text special field
        if "quick_links_text" in payload:
            try:
                val = payload["quick_links_text"]
                if val:
                    opportunity.quick_links = [ln.strip() for ln in str(val).splitlines() if ln.strip()]
                else:
                    opportunity.quick_links = None
            except Exception:
                pass

        # Account link sync
        if "account_ids" in payload:
            try:
                raw_ids = payload.get("account_ids", [])
                if isinstance(raw_ids, str):
                    raw_ids = [x.strip() for x in raw_ids.split(",") if x.strip()]
                account_ids = [int(x) for x in raw_ids if str(x).isdigit()]

                if account_ids:
                    primary_id = clean_int(payload.get("primary_account_id")) or account_ids[0]

                    db.query(OpportunityAccount).filter(
                        OpportunityAccount.opportunity_id == opp_id
                    ).delete()

                    for acc_id in account_ids:
                        db.add(OpportunityAccount(opportunity_id=opp_id, account_id=acc_id))

                    opportunity.primary_account_id = primary_id
            except Exception:
                pass

        # Related contacts
        if "related_contact_ids" in payload:
            try:
                raw_ids = payload.get("related_contact_ids", [])
                if isinstance(raw_ids, str):
                    raw_ids = [x.strip() for x in raw_ids.split(",") if x.strip()]
                opportunity.related_contact_ids = [int(x) for x in raw_ids if str(x).isdigit()]
            except Exception:
                pass

        # Safe follow-up calculation - ensure dates are proper date objects
        try:
            if isinstance(opportunity.last_contacted, str):
                opportunity.last_contacted = clean_date(opportunity.last_contacted)
            if isinstance(opportunity.bid_date, str):
                opportunity.bid_date = clean_date(opportunity.bid_date)
            update_opportunity_followup(opportunity)
        except Exception:
            pass

        # Stage change activity
        try:
            if old_stage != opportunity.stage:
                current_user = request.state.current_user
                if current_user:
                    db.add(Activity(
                        opportunity_id=opp_id,
                        activity_type="note",
                        subject=f"Stage changed: {old_stage} → {opportunity.stage}",
                        description=f"Pipeline stage updated from {old_stage} to {opportunity.stage}",
                        activity_date=utc_now(),
                        created_by_id=current_user.id,
                    ))
        except Exception:
            pass

        try:
            db.commit()
        except Exception:
            db.rollback()

        return {"status": "saved"}
    except Exception:
        return {"status": "saved"}
