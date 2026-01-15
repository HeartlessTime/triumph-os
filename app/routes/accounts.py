from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func
from datetime import date

from app.database import get_db
from app.models import Account, Opportunity, Contact
from app.services.validators import validate_account

router = APIRouter(prefix="/accounts", tags=["accounts"])
templates = Jinja2Templates(directory="app/templates")


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Prepend https:// if URL doesn't start with http:// or https://."""
    if not url:
        return None
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


@router.get("", response_class=HTMLResponse)
async def list_accounts(
    request: Request,
    search: str = None,
    industry: str = None,
    account_type: str = None,
    sort: str = None,
    db: Session = Depends(get_db),
):
    """List all accounts with optional filtering."""
    # Eager load contacts and opportunities to avoid N+1 for:
    # - account.contacts (for length count in template)
    # - account.last_contacted property (iterates contacts)
    # - account.open_opportunities_count property (iterates opportunities)
    # - account.total_pipeline_value property (iterates opportunities)
    query = db.query(Account).options(
        selectinload(Account.contacts), selectinload(Account.opportunities)
    )

    if search:
        query = query.filter(
            or_(
                Account.name.ilike(f"%{search}%"),
                Account.city.ilike(f"%{search}%"),
            )
        )

    if industry:
        query = query.filter(Account.industry == industry)

    if account_type:
        query = query.filter(Account.account_type == account_type)

    # SQL-safe sorting (only real DB columns)
    if sort == "name":
        query = query.order_by(Account.name.asc())
    elif sort == "value":
        # Subquery needed because total_pipeline_value is a Python property
        pipeline_subq = (
            db.query(
                Opportunity.account_id,
                func.sum(Opportunity.lv_value + Opportunity.hdd_value).label(
                    "total_value"
                ),
            )
            .filter(Opportunity.stage.notin_(["Won", "Lost"]))
            .group_by(Opportunity.account_id)
            .subquery()
        )
        query = query.outerjoin(
            pipeline_subq, Account.id == pipeline_subq.c.account_id
        ).order_by(pipeline_subq.c.total_value.desc().nullslast())
    elif sort != "last_contacted":
        # Default sort (skip if last_contacted - handled in Python below)
        query = query.order_by(Account.name.asc())

    accounts = query.all()

    # Python-side sort for last_contacted (it's a @property, not a DB column)
    if sort == "last_contacted":
        accounts.sort(
            key=lambda a: a.last_contacted or date.min,
            reverse=False,  # Oldest first (those not contacted recently at top)
        )

    return templates.TemplateResponse(
        "accounts/list.html",
        {
            "request": request,
            "accounts": accounts,
            "search": search,
            "industry": industry,
            "industries": Account.INDUSTRIES,
            "account_type": account_type,
            "account_types": Account.ACCOUNT_TYPES,
            "sort": sort,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_account_form(request: Request, db: Session = Depends(get_db)):
    """Display new account form."""
    return templates.TemplateResponse(
        "accounts/form.html",
        {
            "request": request,
            "account": None,
            "industries": Account.INDUSTRIES,
            "is_new": True,
            "error": None,
            "warnings": [],
        },
    )


@router.post("/new")
async def create_account(
    request: Request,
    name: str = Form(...),
    account_type: str = Form("end_user"),
    industry: str = Form(None),
    website: str = Form(None),
    phone: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    zip_code: str = Form(None),
    notes: str = Form(None),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Create a new account with validation."""
    current_user = request.state.current_user

    # Build data dict for validation
    data = {
        "name": name,
        "industry": industry,
        "city": city,
        "state": state,
    }

    # Validate account data
    result = validate_account(data, db, existing_id=None)

    # If errors, re-render form with error message
    if not result.is_valid:
        return templates.TemplateResponse(
            "accounts/form.html",
            {
                "request": request,
                "account": None,
                "industries": Account.INDUSTRIES,
                "is_new": True,
                "error": "; ".join(result.errors),
                "warnings": [],
                # Preserve form values
                "form_name": name,
                "form_account_type": account_type,
                "form_industry": industry,
                "form_website": website,
                "form_phone": phone,
                "form_address": address,
                "form_city": city,
                "form_state": state,
                "form_zip_code": zip_code,
                "form_notes": notes,
            },
        )

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        return templates.TemplateResponse(
            "accounts/form.html",
            {
                "request": request,
                "account": None,
                "industries": Account.INDUSTRIES,
                "is_new": True,
                "error": None,
                "warnings": result.warnings,
                # Preserve form values
                "form_name": name,
                "form_account_type": account_type,
                "form_industry": industry,
                "form_website": website,
                "form_phone": phone,
                "form_address": address,
                "form_city": city,
                "form_state": state,
                "form_zip_code": zip_code,
                "form_notes": notes,
            },
        )

    # Create account with ownership
    account = Account(
        name=name,
        account_type=account_type or "end_user",
        industry=industry or None,
        website=normalize_url(website),
        phone=phone or None,
        address=address or None,
        city=city or None,
        state=state or None,
        zip_code=zip_code or None,
        notes=notes or None,
        created_by_id=current_user.id,
    )

    db.add(account)
    db.commit()

    return RedirectResponse(url=f"/accounts/{account.id}", status_code=303)


@router.get("/{account_id}", response_class=HTMLResponse)
async def view_account(
    request: Request, account_id: int, db: Session = Depends(get_db)
):
    """View account details."""
    # Eager load contacts and opportunities to avoid N+1 in template
    # Template accesses account.contacts (list) and account.opportunities (list)
    account = (
        db.query(Account)
        .options(selectinload(Account.contacts), selectinload(Account.opportunities))
        .filter(Account.id == account_id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return templates.TemplateResponse(
        "accounts/view.html",
        {
            "request": request,
            "account": account,
        },
    )


@router.get("/{account_id}/edit", response_class=HTMLResponse)
async def edit_account_form(
    request: Request, account_id: int, db: Session = Depends(get_db)
):
    """Display edit account form."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Normalize website URL for display (ensure https:// prefix)
    display_website = normalize_url(account.website) if account.website else None

    return templates.TemplateResponse(
        "accounts/form.html",
        {
            "request": request,
            "account": account,
            "display_website": display_website,
            "industries": Account.INDUSTRIES,
            "is_new": False,
            "error": None,
            "warnings": [],
        },
    )


@router.post("/{account_id}/edit")
async def update_account(
    request: Request,
    account_id: int,
    name: str = Form(...),
    account_type: str = Form("end_user"),
    industry: str = Form(None),
    website: str = Form(None),
    phone: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    zip_code: str = Form(None),
    notes: str = Form(None),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Update an existing account with validation."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Build data dict for validation
    data = {
        "name": name,
        "industry": industry,
        "city": city,
        "state": state,
    }

    # Validate account data (exclude self from duplicate check)
    result = validate_account(data, db, existing_id=account_id)

    # If errors, re-render form with error message
    if not result.is_valid:
        return templates.TemplateResponse(
            "accounts/form.html",
            {
                "request": request,
                "account": account,
                "display_website": normalize_url(website),
                "industries": Account.INDUSTRIES,
                "is_new": False,
                "error": "; ".join(result.errors),
                "warnings": [],
                # Override with submitted values
                "form_name": name,
                "form_account_type": account_type,
                "form_industry": industry,
                "form_website": website,
                "form_phone": phone,
                "form_address": address,
                "form_city": city,
                "form_state": state,
                "form_zip_code": zip_code,
                "form_notes": notes,
            },
        )

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        return templates.TemplateResponse(
            "accounts/form.html",
            {
                "request": request,
                "account": account,
                "display_website": normalize_url(website),
                "industries": Account.INDUSTRIES,
                "is_new": False,
                "error": None,
                "warnings": result.warnings,
                # Override with submitted values
                "form_name": name,
                "form_account_type": account_type,
                "form_industry": industry,
                "form_website": website,
                "form_phone": phone,
                "form_address": address,
                "form_city": city,
                "form_state": state,
                "form_zip_code": zip_code,
                "form_notes": notes,
            },
        )

    account.name = name
    account.account_type = account_type or "end_user"
    account.industry = industry or None
    account.website = normalize_url(website)
    account.phone = phone or None
    account.address = address or None
    account.city = city or None
    account.state = state or None
    account.zip_code = zip_code or None
    account.notes = notes or None

    db.commit()

    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@router.post("/{account_id}/delete")
async def delete_account(
    request: Request, account_id: int, db: Session = Depends(get_db)
):
    """Delete an account with safety checks."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Block deletion if account has any opportunities
    opp_count = (
        db.query(Opportunity).filter(Opportunity.account_id == account_id).count()
    )
    if opp_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete account with {opp_count} opportunity(ies). Delete opportunities first.",
        )

    # Delete all contacts under this account
    db.query(Contact).filter(Contact.account_id == account_id).delete()

    db.delete(account)
    db.commit()

    return RedirectResponse(url="/accounts", status_code=303)


# -----------------------------
# API Endpoints (JSON)
# -----------------------------
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional


class QuickCreateAccountRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


@router.get("/api/{account_id}/contacts")
async def api_get_account_contacts(account_id: int, db: Session = Depends(get_db)):
    """API: Get contacts for a specific account (JSON response)."""
    contacts = (
        db.query(Contact)
        .filter(Contact.account_id == account_id)
        .order_by(Contact.last_name)
        .all()
    )
    return [
        {"id": c.id, "full_name": c.full_name, "email": c.email, "phone": c.phone}
        for c in contacts
    ]


@router.post("/api/quick-create")
async def api_quick_create_account(
    request: Request,
    data: QuickCreateAccountRequest,
    db: Session = Depends(get_db),
):
    """API: Quick create an account from intake modal (JSON response)."""
    current_user = request.state.current_user

    account = Account(
        name=data.name,
        phone=data.phone or None,
        address=data.address or None,
        created_by_id=current_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    return {"id": account.id, "name": account.name}
