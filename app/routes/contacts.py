from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models import Contact, Account


def update_contact_followup(contact: Contact):
    """Update next_followup to 30 days from last_contacted after logging contact."""
    contact.next_followup = contact.last_contacted + timedelta(days=30)

router = APIRouter(prefix="/contacts", tags=["contacts"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def list_contacts(
    request: Request,
    search: str = None,
    account_id: int = None,
    db: Session = Depends(get_db)
):
    """List all contacts with optional filtering."""
    query = db.query(Contact).join(Account)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Contact.first_name.ilike(search_term)) |
            (Contact.last_name.ilike(search_term)) |
            (Contact.email.ilike(search_term)) |
            (Account.name.ilike(search_term))
        )

    if account_id:
        query = query.filter(Contact.account_id == account_id)

    contacts = query.order_by(Contact.last_name, Contact.first_name).all()
    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse("contacts/list.html", {
        "request": request,
        "contacts": contacts,
        "accounts": accounts,
        "search": search,
        "account_id": account_id,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_contact_form(
    request: Request,
    account_id: int = None,
    db: Session = Depends(get_db)
):
    """Display new contact form."""
    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse("contacts/form.html", {
        "request": request,
        "contact": None,
        "accounts": accounts,
        "selected_account_id": account_id,
        "is_new": True,
    })


@router.post("/new")
async def create_contact(
    request: Request,
    account_id: int = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    title: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    mobile: str = Form(None),
    is_primary: bool = Form(False),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new contact."""
    # Verify account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # If this contact is primary, unset other primary contacts for this account
    if is_primary:
        db.query(Contact).filter(
            Contact.account_id == account_id,
            Contact.is_primary == True
        ).update({"is_primary": False})

    contact = Contact(
        account_id=account_id,
        first_name=first_name,
        last_name=last_name,
        title=title or None,
        email=email or None,
        phone=phone or None,
        mobile=mobile or None,
        is_primary=is_primary,
        notes=notes or None,
    )

    db.add(contact)
    db.commit()

    # Redirect based on where we came from
    redirect_url = request.query_params.get("next", f"/accounts/{account_id}")
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/{contact_id}", response_class=HTMLResponse)
async def view_contact(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db)
):
    """View contact details."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return templates.TemplateResponse("contacts/view.html", {
        "request": request,
        "contact": contact,
        "today": date.today(),
    })


@router.get("/{contact_id}/edit", response_class=HTMLResponse)
async def edit_contact_form(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db)
):
    """Display edit contact form."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse("contacts/form.html", {
        "request": request,
        "contact": contact,
        "accounts": accounts,
        "selected_account_id": contact.account_id,
        "is_new": False,
    })


@router.post("/{contact_id}/edit")
async def update_contact(
    request: Request,
    contact_id: int,
    account_id: int = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    title: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    mobile: str = Form(None),
    is_primary: bool = Form(False),
    notes: str = Form(None),
    last_contacted: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update an existing contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # If this contact is becoming primary, unset other primary contacts
    if is_primary and not contact.is_primary:
        db.query(Contact).filter(
            Contact.account_id == account_id,
            Contact.is_primary == True,
            Contact.id != contact_id
        ).update({"is_primary": False})

    contact.account_id = account_id
    contact.first_name = first_name
    contact.last_name = last_name
    contact.title = title or None
    contact.email = email or None
    contact.phone = phone or None
    contact.mobile = mobile or None
    contact.is_primary = is_primary
    contact.notes = notes or None

    if last_contacted:
        contact.last_contacted = datetime.strptime(last_contacted, "%Y-%m-%d").date()

    db.commit()

    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)


@router.post("/{contact_id}/delete")
async def delete_contact(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db)
):
    """Delete a contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    account_id = contact.account_id
    db.delete(contact)
    db.commit()

    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@router.post("/{contact_id}/log-contact")
async def log_contact(
    contact_id: int,
    db: Session = Depends(get_db)
):
    """Log contact - updates last_contacted to today and next_followup to 14 days from now."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.last_contacted = date.today()
    update_contact_followup(contact)
    db.commit()

    # Check referer to redirect back to source page
    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)
