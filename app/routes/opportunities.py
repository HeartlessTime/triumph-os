from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Union
import os

from app.database import get_db
from app.models import (
    Opportunity, OpportunityScope, Account, Contact,
    User, ScopePackage, Activity, Task, Document
)
from app.services.followup import calculate_next_followup, get_followup_status

router = APIRouter(prefix="/opportunities", tags=["opportunities"])
templates = Jinja2Templates(directory="app/templates")


# -----------------------------
# Helpers
# -----------------------------
def update_opportunity_followup(opportunity: Opportunity, today: Union[date, None] = None):
    if today is None:
        today = date.today()

    opportunity.next_followup = calculate_next_followup(
        stage=opportunity.stage,
        last_contacted=opportunity.last_contacted,
        bid_date=opportunity.bid_date,
        today=today
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
    db: Session = Depends(get_db)
):
    estimator_id = int(estimator_id) if estimator_id else None

    today = date.today()

    # EXPLICIT JOIN (fixes ambiguous FK error)
    query = (
        db.query(Opportunity)
        .join(Account, Opportunity.account_id == Account.id)
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
            Opportunity.stalled_reason.isnot(None),
            Opportunity.stalled_reason != ''
        )

    opportunities = query.order_by(
        Opportunity.bid_date.nullslast(),
        Opportunity.name
    ).all()

    # Apply sorting
    if sort == 'value':
        opportunities.sort(key=lambda o: (o.value or 0), reverse=True)
    elif sort == 'bid_date':
        opportunities.sort(key=lambda o: (o.bid_date or date.max))
    elif sort == 'last_contacted':
        opportunities.sort(key=lambda o: (o.last_contacted or date.min))
    elif sort == 'next_followup':
        opportunities.sort(key=lambda o: (o.next_followup or date.max))

    for opp in opportunities:
        opp.followup_status = get_followup_status(opp.next_followup, today)

    users = (
        db.query(User)
        .filter(User.is_active == True)
        .order_by(User.full_name)
        .all()
    )

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
        }
    )


# -----------------------------
# Intake Form
# -----------------------------
@router.get("/intake", response_class=HTMLResponse)
async def intake_form(
    request: Request,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    accounts = db.query(Account).order_by(Account.name).all()
    scope_packages = (
        db.query(ScopePackage)
        .filter(ScopePackage.is_active == True)
        .order_by(ScopePackage.sort_order)
        .all()
    )

    users = (
        db.query(User)
        .filter(User.is_active == True)
        .order_by(User.full_name)
        .all()
    )

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
        }
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
    owner_id: Optional[int] = Form(None),
    assigned_estimator_id: Optional[int] = Form(None),
    scope_names: List[str] = Form(default=[]),
    scope_other_text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    def clean_num(val: Optional[str]):
        return Decimal(val.replace(",", "")) if val else None

    opportunity = Opportunity(
        account_id=account_id,
        name=name,
        stage=stage,
        probability=Opportunity.STAGE_PROBABILITIES.get(stage, 0),
        lv_value=clean_num(lv_value),
        hdd_value=clean_num(hdd_value),
        bid_date=datetime.strptime(bid_date, "%Y-%m-%d").date() if bid_date else None,
        owner_id=owner_id,
        assigned_estimator_id=assigned_estimator_id,
        last_contacted=date.today(),
    )

    update_opportunity_followup(opportunity)

    db.add(opportunity)
    db.flush()  # Get the opportunity.id

    # Add scope packages
    for scope_name in scope_names:
        if scope_name == 'Other' and scope_other_text:
            # Use the custom text instead of "Other"
            scope_pkg = db.query(ScopePackage).filter(ScopePackage.name == scope_other_text).first()
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_other_text, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(OpportunityScope(opportunity_id=opportunity.id, scope_package_id=scope_pkg.id))
        else:
            scope_pkg = db.query(ScopePackage).filter(ScopePackage.name == scope_name).first()
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_name, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(OpportunityScope(opportunity_id=opportunity.id, scope_package_id=scope_pkg.id))

    db.commit()

    return RedirectResponse(
        url=f"/opportunities/{opportunity.id}",
        status_code=303
    )


# -----------------------------
# Opportunity Detail
# -----------------------------
@router.get("/{opp_id}", response_class=HTMLResponse)
async def opportunity_detail(
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
):
    today = date.today()

    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opportunity.followup_status = get_followup_status(
        opportunity.next_followup, today
    )

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
        related_contacts = db.query(Contact).filter(Contact.id.in_(opportunity.related_contact_ids)).all()

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
        }
    )


# -----------------------------
# Delete Opportunity
# -----------------------------
@router.post("/{opp_id}/delete")
async def delete_opportunity(
    opp_id: int,
    db: Session = Depends(get_db)
):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    db.delete(opportunity)
    db.commit()

    return RedirectResponse("/opportunities", status_code=303)


# -----------------------------
# Quick Stage Update
# -----------------------------
@router.post("/{opp_id}/update-stage")
async def update_stage(
    opp_id: int,
    stage: str = Form(...),
    db: Session = Depends(get_db)
):
    """Quick update opportunity stage without full edit form."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opportunity.stage = stage
    opportunity.probability = Opportunity.STAGE_PROBABILITIES.get(stage, 0)
    update_opportunity_followup(opportunity)
    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


# -----------------------------
# Log Contact (Quick Action)
# -----------------------------
@router.post("/{opp_id}/log-contact")
async def log_contact(
    opp_id: int,
    db: Session = Depends(get_db)
):
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
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
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

    users = (
        db.query(User)
        .filter(User.is_active == True)
        .order_by(User.full_name)
        .all()
    )

    sales_users = [u for u in users if u.role in ("Sales", "Admin")]
    estimators = [u for u in users if u.role in ("Estimator", "Admin")]

    selected_scope_names = [s.name for s in opportunity.scopes] if opportunity.scopes else []
    selected_scope_other_text = ""
    for s in opportunity.scopes or []:
        if s.name not in [
            'Horizontal Cabling (Copper)', 'Backbone Cabling (Fiber/Copper)',
            'Site / Campus Fiber', 'IDF / MDF Closet Buildout',
            'Security / Access Control', 'Cameras / Surveillance',
            'Wireless / Access Points', 'AV / Paging / Intercom', 'Other'
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
        }
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
    db: Session = Depends(get_db)
):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    def clean_num(val):
        if not val:
            return None
        return Decimal(str(val).replace(",", ""))

    opportunity.account_id = account_id
    opportunity.name = name
    opportunity.stage = stage
    opportunity.probability = Opportunity.STAGE_PROBABILITIES.get(stage, 0)
    opportunity.description = description or None
    opportunity.lv_value = clean_num(lv_value)
    opportunity.hdd_value = clean_num(hdd_value)
    opportunity.bid_date = datetime.strptime(bid_date, "%Y-%m-%d").date() if bid_date else None
    opportunity.bid_time = datetime.strptime(bid_time, "%H:%M").time() if bid_time else None
    opportunity.owner_id = owner_id or None
    opportunity.assigned_estimator_id = assigned_estimator_id or None
    opportunity.primary_contact_id = primary_contact_id or None
    opportunity.source = source or None
    opportunity.notes = notes or None
    opportunity.bid_type = bid_type or None
    opportunity.submission_method = submission_method or None
    opportunity.bid_form_required = bid_form_required == "true" if bid_form_required else None
    opportunity.bond_required = bond_required == "true" if bond_required else None
    opportunity.prevailing_wage = prevailing_wage or None
    opportunity.project_type = project_type or None
    opportunity.rebid = rebid == "true" if rebid else False
    opportunity.known_risks = known_risks or None
    opportunity.stalled_reason = stalled_reason or None
    opportunity.end_user_account_id = end_user_account_id or None

    if last_contacted:
        opportunity.last_contacted = datetime.strptime(last_contacted, "%Y-%m-%d").date()

    if quick_links_text:
        opportunity.quick_links = [link.strip() for link in quick_links_text.strip().split("\n") if link.strip()]
    else:
        opportunity.quick_links = None

    # Update GCs list
    if gc_ids:
        opportunity.gcs = [int(gc_id) for gc_id in gc_ids if gc_id]
    else:
        opportunity.gcs = None

    # Update scope packages - clear existing and re-add
    db.query(OpportunityScope).filter(OpportunityScope.opportunity_id == opp_id).delete()

    for scope_name in scope_names:
        if scope_name == 'Other' and scope_other_text:
            scope_pkg = db.query(ScopePackage).filter(ScopePackage.name == scope_other_text).first()
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_other_text, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(OpportunityScope(opportunity_id=opp_id, scope_package_id=scope_pkg.id))
        else:
            scope_pkg = db.query(ScopePackage).filter(ScopePackage.name == scope_name).first()
            if not scope_pkg:
                scope_pkg = ScopePackage(name=scope_name, is_active=True)
                db.add(scope_pkg)
                db.flush()
            db.add(OpportunityScope(opportunity_id=opp_id, scope_package_id=scope_pkg.id))

    update_opportunity_followup(opportunity)
    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


# -----------------------------
# Calendar View
# -----------------------------
@router.get("/calendar/view", response_class=HTMLResponse)
async def calendar_view(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "opportunities/calendar.html",
        {"request": request}
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
        events.append({
            "id": opp.id,
            "title": opp.name,
            "start": opp.bid_date.isoformat(),
            "url": f"/opportunities/{opp.id}",
            "backgroundColor": "#0d6efd",
            "borderColor": "#0d6efd",
        })

    return JSONResponse(content=events)
