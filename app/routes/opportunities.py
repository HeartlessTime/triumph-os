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
def update_opportunity_followup(opportunity: Opportunity, today: date | None = None):
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
    search: str | None = None,
    stage: str | None = None,
    estimator_id: str | None = None,
    gc_id: str | None = None,
    end_user_account_id: str | None = None,
    db: Session = Depends(get_db)
):
    estimator_id = int(estimator_id) if estimator_id else None
    gc_id = int(gc_id) if gc_id else None
    end_user_account_id = int(end_user_account_id) if end_user_account_id else None

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

    opportunities = query.order_by(
        Opportunity.bid_date.nullslast(),
        Opportunity.name
    ).all()

    # Python-side filters
    if gc_id:
        opportunities = [o for o in opportunities if o.gcs and gc_id in o.gcs]

    if end_user_account_id:
        opportunities = [
            o for o in opportunities if o.end_user_account_id == end_user_account_id
        ]

    for opp in opportunities:
        opp.followup_status = get_followup_status(opp.next_followup, today)

    users = (
        db.query(User)
        .filter(User.is_active == True)
        .order_by(User.full_name)
        .all()
    )

    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse(
        "opportunities/list.html",
        {
            "request": request,
            "opportunities": opportunities,
            "users": users,
            "accounts": accounts,
            "stages": Opportunity.STAGE_NAMES,
            "search": search,
            "stage": stage,
            "estimator_id": estimator_id,
            "gc_id": gc_id,
            "end_user_account_id": end_user_account_id,
        }
    )


# -----------------------------
# Intake Form
# -----------------------------
@router.get("/intake", response_class=HTMLResponse)
async def intake_form(
    request: Request,
    account_id: int | None = None,
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
    lv_value: str | None = Form(None),
    hdd_value: str | None = Form(None),
    bid_date: str | None = Form(None),
    owner_id: int | None = Form(None),
    assigned_estimator_id: int | None = Form(None),
    db: Session = Depends(get_db)
):
    def clean_num(val: str | None):
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

    return templates.TemplateResponse(
        "opportunities/command_center.html",
        {
            "request": request,
            "opportunity": opportunity,
            "today": today,
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
