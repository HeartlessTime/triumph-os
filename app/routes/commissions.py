from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.account import Account
from app.models.contact import Contact
from app.models.commission_entry import CommissionEntry
from app.template_config import templates

router = APIRouter(prefix="/commissions", tags=["commissions"])

COMMISSION_RATE = Decimal("0.01")


def _parse_decimal(value: Optional[str]) -> Optional[Decimal]:
    if not value or value.strip() == "":
        return None
    try:
        return Decimal(value.strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _calc_commission(job_amount: Optional[Decimal]) -> Optional[Decimal]:
    if job_amount is None:
        return None
    return (job_amount * COMMISSION_RATE).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# List view
# ---------------------------------------------------------------------------
@router.get("", response_class=HTMLResponse)
async def commission_list(request: Request, db: Session = Depends(get_db)):
    month = request.query_params.get("month")
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")

    # Compute prev/next months and display label
    try:
        dt = datetime.strptime(month, "%Y-%m")
    except ValueError:
        dt = datetime.utcnow().replace(day=1)

    if dt.month == 1:
        prev_dt = dt.replace(year=dt.year - 1, month=12)
    else:
        prev_dt = dt.replace(month=dt.month - 1)

    if dt.month == 12:
        next_dt = dt.replace(year=dt.year + 1, month=1)
    else:
        next_dt = dt.replace(month=dt.month + 1)

    entries = (
        db.query(CommissionEntry)
        .filter(CommissionEntry.month == month)
        .order_by(CommissionEntry.account_name, CommissionEntry.job_name)
        .all()
    )

    accounts = (
        db.query(Account)
        .options(selectinload(Account.contacts))
        .order_by(Account.name)
        .all()
    )

    # Build account_name -> last_contacted lookup
    account_last_contacted = {}
    for acct in accounts:
        if acct.last_contacted:
            account_last_contacted[acct.name] = acct.last_contacted

    # Only "Won" entries count toward the total
    total_commission = (
        db.query(func.sum(CommissionEntry.commission_amount))
        .filter(
            CommissionEntry.month == month,
            CommissionEntry.job_status == "Won",
        )
        .scalar()
    ) or Decimal("0")

    return templates.TemplateResponse(
        "commissions/list.html",
        {
            "request": request,
            "entries": entries,
            "selected_month": month,
            "month_label": dt.strftime("%B %Y"),
            "prev_month": prev_dt.strftime("%Y-%m"),
            "next_month": next_dt.strftime("%Y-%m"),
            "accounts": accounts,
            "total_commission": total_commission,
            "job_statuses": CommissionEntry.JOB_STATUSES,
            "account_last_contacted": account_last_contacted,
        },
    )


# ---------------------------------------------------------------------------
# JSON: contacts for a given account
# ---------------------------------------------------------------------------
@router.get("/api/contacts/{account_id}", response_class=JSONResponse)
async def get_contacts_for_account(account_id: int, db: Session = Depends(get_db)):
    contacts = (
        db.query(Contact)
        .filter(Contact.account_id == account_id)
        .order_by(Contact.first_name)
        .all()
    )
    return [{"id": c.id, "name": c.full_name} for c in contacts]


# ---------------------------------------------------------------------------
# Add entry
# ---------------------------------------------------------------------------
@router.post("/add")
async def add_commission(
    request: Request,
    month: str = Form(...),
    account_name: str = Form(...),
    job_name: str = Form(...),
    job_number: str = Form(""),
    contact: str = Form(""),
    job_amount: str = Form(""),
    notes: str = Form(""),
    job_status: str = Form("Pending"),
    db: Session = Depends(get_db),
):
    parsed_job_amount = _parse_decimal(job_amount)
    safe_status = job_status if job_status in CommissionEntry.JOB_STATUSES else "Pending"
    entry = CommissionEntry(
        month=month.strip(),
        account_name=account_name.strip(),
        job_name=job_name.strip(),
        job_number=job_number.strip() or None,
        contact=contact.strip() or None,
        job_amount=parsed_job_amount,
        commission_amount=_calc_commission(parsed_job_amount),
        notes=notes.strip() or None,
        job_status=safe_status,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse(url=f"/commissions?month={entry.month}", status_code=303)


# ---------------------------------------------------------------------------
# Edit entry
# ---------------------------------------------------------------------------
@router.post("/{entry_id}/edit")
async def edit_commission(
    entry_id: int,
    request: Request,
    month: str = Form(...),
    account_name: str = Form(...),
    job_name: str = Form(...),
    job_number: str = Form(""),
    contact: str = Form(""),
    job_amount: str = Form(""),
    notes: str = Form(""),
    job_status: str = Form("Pending"),
    db: Session = Depends(get_db),
):
    entry = db.query(CommissionEntry).filter(CommissionEntry.id == entry_id).first()
    if not entry:
        return RedirectResponse(url="/commissions", status_code=303)

    parsed_job_amount = _parse_decimal(job_amount)
    entry.month = month.strip()
    entry.account_name = account_name.strip()
    entry.job_name = job_name.strip()
    entry.job_number = job_number.strip() or None
    entry.contact = contact.strip() or None
    entry.job_amount = parsed_job_amount
    entry.commission_amount = _calc_commission(parsed_job_amount)
    entry.notes = notes.strip() or None
    entry.job_status = job_status if job_status in CommissionEntry.JOB_STATUSES else "Pending"
    entry.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/commissions?month={entry.month}", status_code=303)


# ---------------------------------------------------------------------------
# Quick status update (JSON)
# ---------------------------------------------------------------------------
@router.post("/{entry_id}/status", response_class=JSONResponse)
async def update_commission_status(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.json()
    new_status = body.get("job_status", "Pending")
    if new_status not in CommissionEntry.JOB_STATUSES:
        return JSONResponse({"error": "Invalid status"}, status_code=400)

    entry = db.query(CommissionEntry).filter(CommissionEntry.id == entry_id).first()
    if not entry:
        return JSONResponse({"error": "Not found"}, status_code=404)

    entry.job_status = new_status
    entry.updated_at = datetime.utcnow()
    db.commit()

    # Recompute won-only total for this month
    total = (
        db.query(func.sum(CommissionEntry.commission_amount))
        .filter(CommissionEntry.month == entry.month, CommissionEntry.job_status == "Won")
        .scalar()
    ) or 0
    return {"ok": True, "job_status": new_status, "total_commission": float(total)}


# ---------------------------------------------------------------------------
# Delete entry
# ---------------------------------------------------------------------------
@router.post("/{entry_id}/delete")
async def delete_commission(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    entry = db.query(CommissionEntry).filter(CommissionEntry.id == entry_id).first()
    redirect_month = entry.month if entry else datetime.utcnow().strftime("%Y-%m")
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse(url=f"/commissions?month={redirect_month}", status_code=303)
