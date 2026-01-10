from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])
templates = Jinja2Templates(directory="app/templates")


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Prepend https:// if URL doesn't start with http:// or https://."""
    if not url:
        return None
    url = url.strip()
    if url and not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url


@router.get("", response_class=HTMLResponse)
async def list_accounts(
    request: Request,
    search: str = None,
    industry: str = None,
    sort: str = None,
    db: Session = Depends(get_db)
):
    """List all accounts with optional filtering."""
    query = db.query(Account)

    if search:
        query = query.filter(
            or_(
                Account.name.ilike(f"%{search}%"),
                Account.city.ilike(f"%{search}%"),
            )
        )

    if industry:
        query = query.filter(Account.industry == industry)

    accounts = query.order_by(Account.name).all()

    # Apply sorting
    if sort == 'name':
        accounts.sort(key=lambda a: (a.name or '').lower())
    elif sort == 'last_contacted':
        from datetime import date
        accounts.sort(key=lambda a: (a.last_contacted or date.min))
    elif sort == 'value':
        accounts.sort(key=lambda a: (a.total_pipeline_value or 0), reverse=True)

    return templates.TemplateResponse("accounts/list.html", {
        "request": request,
        "accounts": accounts,
        "search": search,
        "industry": industry,
        "industries": Account.INDUSTRIES,
        "sort": sort,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_account_form(
    request: Request,
    db: Session = Depends(get_db)
):
    """Display new account form."""
    return templates.TemplateResponse("accounts/form.html", {
        "request": request,
        "account": None,
        "industries": Account.INDUSTRIES,
        "is_new": True,
    })


@router.post("/new")
async def create_account(
    request: Request,
    name: str = Form(...),
    industry: str = Form(None),
    website: str = Form(None),
    phone: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    zip_code: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new account."""
    account = Account(
        name=name,
        industry=industry or None,
        website=normalize_url(website),
        phone=phone or None,
        address=address or None,
        city=city or None,
        state=state or None,
        zip_code=zip_code or None,
        notes=notes or None,
    )

    db.add(account)
    db.commit()

    return RedirectResponse(url=f"/accounts/{account.id}", status_code=303)


@router.get("/{account_id}", response_class=HTMLResponse)
async def view_account(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db)
):
    """View account details."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return templates.TemplateResponse("accounts/view.html", {
        "request": request,
        "account": account,
    })


@router.get("/{account_id}/edit", response_class=HTMLResponse)
async def edit_account_form(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db)
):
    """Display edit account form."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Normalize website URL for display (ensure https:// prefix)
    display_website = normalize_url(account.website) if account.website else None

    return templates.TemplateResponse("accounts/form.html", {
        "request": request,
        "account": account,
        "display_website": display_website,
        "industries": Account.INDUSTRIES,
        "is_new": False,
    })


@router.post("/{account_id}/edit")
async def update_account(
    request: Request,
    account_id: int,
    name: str = Form(...),
    industry: str = Form(None),
    website: str = Form(None),
    phone: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    zip_code: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update an existing account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.name = name
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
    request: Request,
    account_id: int,
    db: Session = Depends(get_db)
):
    """Delete an account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    db.delete(account)
    db.commit()

    return RedirectResponse(url="/accounts", status_code=303)
