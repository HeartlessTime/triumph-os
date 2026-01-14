from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models import Contact, Account, Opportunity, Activity
from app.services.followup import calculate_next_followup
from app.services.validators import validate_contact


def update_contact_followup(contact: Contact):
    """Update next_followup to 30 days from last_contacted after logging contact."""
    contact.next_followup = contact.last_contacted + timedelta(days=30)


router = APIRouter(prefix="/contacts", tags=["contacts"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def list_contacts(
    request: Request,
    search: str = None,
    account_id: str = None,
    db: Session = Depends(get_db),
):
    """List all contacts with optional filtering."""
    # Safely convert account_id (treat "" as None)
    account_id_int = int(account_id) if account_id else None

    # Eager load account to avoid N+1 when template accesses contact.account.name
    query = db.query(Contact).options(selectinload(Contact.account)).join(Account)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Contact.first_name.ilike(search_term))
            | (Contact.last_name.ilike(search_term))
            | (Contact.email.ilike(search_term))
            | (Account.name.ilike(search_term))
        )

    if account_id_int:
        query = query.filter(Contact.account_id == account_id_int)

    contacts = query.order_by(Contact.last_name, Contact.first_name).all()
    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse(
        "contacts/list.html",
        {
            "request": request,
            "contacts": contacts,
            "accounts": accounts,
            "search": search,
            "account_id": account_id_int,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_contact_form(
    request: Request, account_id: str = None, db: Session = Depends(get_db)
):
    """Display new contact form."""
    # Safely convert account_id (treat "" as None)
    account_id_int = int(account_id) if account_id else None

    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse(
        "contacts/form.html",
        {
            "request": request,
            "contact": None,
            "accounts": accounts,
            "selected_account_id": account_id_int,
            "is_new": True,
            "error": None,
            "warnings": [],
        },
    )


@router.post("/new")
async def create_contact(
    request: Request,
    account_id: int = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(None),
    title: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    mobile: str = Form(None),
    is_primary: bool = Form(False),
    notes: str = Form(None),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Create a new contact with validation."""
    accounts = db.query(Account).order_by(Account.name).all()

    # Build data dict for validation
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "account_id": account_id,
        "email": email,
        "phone": phone,
        "mobile": mobile,
    }

    # Validate contact data
    result = validate_contact(data, db, existing_id=None)

    # If errors, re-render form with error message
    if not result.is_valid:
        return templates.TemplateResponse(
            "contacts/form.html",
            {
                "request": request,
                "contact": None,
                "accounts": accounts,
                "selected_account_id": account_id,
                "is_new": True,
                "error": "; ".join(result.errors),
                "warnings": [],
                # Preserve form values
                "form_first_name": first_name,
                "form_last_name": last_name,
                "form_title": title,
                "form_email": email,
                "form_phone": phone,
                "form_mobile": mobile,
                "form_is_primary": is_primary,
                "form_notes": notes,
            },
        )

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        return templates.TemplateResponse(
            "contacts/form.html",
            {
                "request": request,
                "contact": None,
                "accounts": accounts,
                "selected_account_id": account_id,
                "is_new": True,
                "error": None,
                "warnings": result.warnings,
                # Preserve form values
                "form_first_name": first_name,
                "form_last_name": last_name,
                "form_title": title,
                "form_email": email,
                "form_phone": phone,
                "form_mobile": mobile,
                "form_is_primary": is_primary,
                "form_notes": notes,
            },
        )

    # Verify account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # If this contact is primary, unset other primary contacts for this account
    if is_primary:
        db.query(Contact).filter(
            Contact.account_id == account_id, Contact.is_primary == True
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
    request: Request, contact_id: int, db: Session = Depends(get_db)
):
    """View contact details."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return templates.TemplateResponse(
        "contacts/view.html",
        {
            "request": request,
            "contact": contact,
            "today": date.today(),
        },
    )


@router.get("/{contact_id}/edit", response_class=HTMLResponse)
async def edit_contact_form(
    request: Request, contact_id: int, db: Session = Depends(get_db)
):
    """Display edit contact form."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse(
        "contacts/form.html",
        {
            "request": request,
            "contact": contact,
            "accounts": accounts,
            "selected_account_id": contact.account_id,
            "is_new": False,
            "error": None,
            "warnings": [],
        },
    )


@router.post("/{contact_id}/edit")
async def update_contact(
    request: Request,
    contact_id: int,
    account_id: int = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(None),
    title: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    mobile: str = Form(None),
    is_primary: bool = Form(False),
    notes: str = Form(None),
    last_contacted: str = Form(None),
    confirm_warnings: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Update an existing contact with validation."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    accounts = db.query(Account).order_by(Account.name).all()

    # Build data dict for validation
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "account_id": account_id,
        "email": email,
        "phone": phone,
        "mobile": mobile,
    }

    # Validate contact data (exclude self from duplicate check)
    result = validate_contact(data, db, existing_id=contact_id)

    # If errors, re-render form with error message
    if not result.is_valid:
        return templates.TemplateResponse(
            "contacts/form.html",
            {
                "request": request,
                "contact": contact,
                "accounts": accounts,
                "selected_account_id": account_id,
                "is_new": False,
                "error": "; ".join(result.errors),
                "warnings": [],
                # Preserve form values
                "form_first_name": first_name,
                "form_last_name": last_name,
                "form_title": title,
                "form_email": email,
                "form_phone": phone,
                "form_mobile": mobile,
                "form_is_primary": is_primary,
                "form_notes": notes,
            },
        )

    # If warnings and not confirmed, show warnings
    if result.warnings and not confirm_warnings:
        return templates.TemplateResponse(
            "contacts/form.html",
            {
                "request": request,
                "contact": contact,
                "accounts": accounts,
                "selected_account_id": account_id,
                "is_new": False,
                "error": None,
                "warnings": result.warnings,
                # Preserve form values
                "form_first_name": first_name,
                "form_last_name": last_name,
                "form_title": title,
                "form_email": email,
                "form_phone": phone,
                "form_mobile": mobile,
                "form_is_primary": is_primary,
                "form_notes": notes,
            },
        )

    # If this contact is becoming primary, unset other primary contacts
    if is_primary and not contact.is_primary:
        db.query(Contact).filter(
            Contact.account_id == account_id,
            Contact.is_primary == True,
            Contact.id != contact_id,
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

    # Handle last_contacted - allow clearing by setting to None when empty
    if last_contacted and last_contacted.strip():
        contact.last_contacted = datetime.strptime(last_contacted, "%Y-%m-%d").date()
    else:
        contact.last_contacted = None

    db.commit()

    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)


@router.post("/{contact_id}/delete")
async def delete_contact(
    request: Request, contact_id: int, db: Session = Depends(get_db)
):
    """Delete a contact with proper cleanup."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    account_id = contact.account_id

    # Remove this contact from opportunities (primary_contact_id)
    db.query(Opportunity).filter(Opportunity.primary_contact_id == contact_id).update(
        {"primary_contact_id": None}
    )

    # Remove from related_contact_ids (JSON array) in opportunities
    opps_with_related = (
        db.query(Opportunity).filter(Opportunity.related_contact_ids.isnot(None)).all()
    )
    for opp in opps_with_related:
        if opp.related_contact_ids and contact_id in opp.related_contact_ids:
            opp.related_contact_ids = [
                cid for cid in opp.related_contact_ids if cid != contact_id
            ]
            if not opp.related_contact_ids:
                opp.related_contact_ids = None

    # Delete activities linked to this contact
    db.query(Activity).filter(Activity.contact_id == contact_id).delete()

    db.delete(contact)
    db.commit()

    return RedirectResponse(url=f"/accounts/{account_id}", status_code=303)


@router.post("/{contact_id}/log-meeting")
async def log_meeting(
    request: Request,
    contact_id: int,
    meeting_date: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db),
):
    """Log a meeting with a contact.

    Creates an Activity with type="meeting" for the contact.
    Updates last_contacted to the meeting date.
    """
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    current_user = request.state.current_user

    # Parse meeting date or default to today
    if meeting_date:
        meeting_dt = datetime.strptime(meeting_date, "%Y-%m-%d")
    else:
        meeting_dt = datetime.now()

    # Create the meeting activity
    meeting_activity = Activity(
        opportunity_id=None,
        activity_type="meeting",
        subject=f"Meeting with {contact.full_name}",
        description=notes.strip() if notes and notes.strip() else None,
        activity_date=meeting_dt,
        contact_id=contact_id,
        created_by_id=current_user.id,
    )
    db.add(meeting_activity)

    # Update last_contacted on the contact
    contact.last_contacted = meeting_dt.date()
    update_contact_followup(contact)

    db.commit()

    # Redirect to 'from' param if provided, otherwise to contact detail
    redirect_url = request.query_params.get("from") or request.query_params.get("next") or f"/contacts/{contact_id}"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/{contact_id}/log-contact")
async def log_contact(
    request: Request,
    contact_id: int,
    activity_type: str = Form(...),  # Required - no default, must come from modal form
    notes: str = Form(None),
    db: Session = Depends(get_db),
):
    """Log contact - updates last_contacted to today and next_followup to 30 days from now.

    Creates a follow-up Activity for the contact (appears in summaries/audit log).
    Also creates Activity entries on all related opportunities.
    """
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.last_contacted = date.today()
    update_contact_followup(contact)

    current_user = request.state.current_user

    # Build description from notes or default
    description = notes.strip() if notes and notes.strip() else f"Logged contact with {contact.full_name} at {contact.account.name}"

    # Always create a contact-level follow-up Activity (no opportunity required)
    # This ensures the follow-up appears in weekly summaries and audit log
    followup_activity = Activity(
        opportunity_id=None,
        activity_type=activity_type,
        subject=f"Follow-up with {contact.full_name}",
        description=description,
        activity_date=datetime.now(),
        contact_id=contact_id,
        created_by_id=current_user.id,
    )
    db.add(followup_activity)

    # Find all opportunities where this contact is the primary contact
    related_opps = (
        db.query(Opportunity)
        .filter(
            Opportunity.primary_contact_id == contact_id,
            Opportunity.stage.notin_(["Won", "Lost"]),
        )
        .all()
    )

    # Create additional Activity entries on each related opportunity
    for opp in related_opps:
        activity = Activity(
            opportunity_id=opp.id,
            activity_type=activity_type,
            subject=f"Contacted {contact.full_name}",
            description=f"Contacted {contact.full_name} regarding {opp.name}",
            activity_date=datetime.now(),
            contact_id=contact_id,
            created_by_id=current_user.id,
        )
        db.add(activity)
        # Update the opportunity's last_contacted and recalculate next_followup
        opp.last_contacted = date.today()
        opp.next_followup = calculate_next_followup(
            stage=opp.stage, last_contacted=opp.last_contacted, bid_date=opp.bid_date
        )

    db.commit()

    # Redirect to 'from' param if provided, otherwise to contact detail
    redirect_url = request.query_params.get("from") or request.query_params.get("next") or f"/contacts/{contact_id}"
    return RedirectResponse(url=redirect_url, status_code=303)
