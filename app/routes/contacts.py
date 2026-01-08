from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, DEMO_MODE
from app.models import Contact, Account
from app.demo_data import get_all_demo_contacts, get_all_demo_accounts

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
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/contacts", status_code=303)

    # DEMO MODE: Use demo data
    if DEMO_MODE or db is None:
        contacts = get_all_demo_contacts()
        accounts = get_all_demo_accounts()

        # Apply filters to demo data
        if search:
            search_lower = search.lower()
            contacts = [c for c in contacts if
                       search_lower in c.first_name.lower() or
                       search_lower in c.last_name.lower() or
                       (c.email and search_lower in c.email.lower())]

        if account_id:
            contacts = [c for c in contacts if c.account_id == account_id]

        contacts.sort(key=lambda c: (c.last_name, c.first_name))
    else:
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
        "user": user,
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
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/contacts/new", status_code=303)

    # DEMO MODE: Show notice
    if DEMO_MODE or db is None:
        return templates.TemplateResponse("demo_mode_notice.html", {
            "request": request,
            "user": user,
            "feature": "Create New Contact",
            "message": "Creating new contacts is disabled in demo mode. Explore the existing demo contacts instead.",
            "back_url": "/contacts",
        })

    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse("contacts/form.html", {
        "request": request,
        "user": user,
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
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # DEMO MODE: Redirect to contacts list
    if DEMO_MODE or db is None:
        return RedirectResponse(url="/contacts", status_code=303)

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
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/contacts/{contact_id}", status_code=303)

    # DEMO MODE: Find contact in demo data
    if DEMO_MODE or db is None:
        contacts = get_all_demo_contacts()
        contact = next((c for c in contacts if c.id == contact_id), None)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
    else:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

    return templates.TemplateResponse("contacts/view.html", {
        "request": request,
        "user": user,
        "contact": contact,
    })


@router.get("/{contact_id}/edit", response_class=HTMLResponse)
async def edit_contact_form(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db)
):
    """Display edit contact form."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/contacts/{contact_id}/edit", status_code=303)

    # DEMO MODE: Show notice
    if DEMO_MODE or db is None:
        return templates.TemplateResponse("demo_mode_notice.html", {
            "request": request,
            "user": user,
            "feature": "Edit Contact",
            "message": "Editing contacts is disabled in demo mode. This feature is view-only.",
            "back_url": f"/contacts/{contact_id}",
        })

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse("contacts/form.html", {
        "request": request,
        "user": user,
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
    db: Session = Depends(get_db)
):
    """Update an existing contact."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if DEMO_MODE or db is None:
        return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)
    
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
    
    db.commit()
    
    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)


@router.post("/{contact_id}/delete")
async def delete_contact(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db)
):
    """Delete a contact."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if DEMO_MODE or db is None:
        return RedirectResponse(url=f"/accounts/", status_code=303)
    
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    account_id = contact.account_id
    db.delete(contact)
    db.commit()
    
    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)
