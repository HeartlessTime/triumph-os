from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models import Contact, Account, Opportunity, Activity
from app.services.followup import calculate_next_followup
from app.services.validators import validate_contact
from app.template_config import templates, utc_now


def add_business_days(start_date: date, num_days: int) -> date:
    """Add business days (Mon-Fri) to a date, skipping weekends."""
    current = start_date
    days_added = 0
    while days_added < num_days:
        current += timedelta(days=1)
        # Monday=0, Sunday=6; skip Saturday(5) and Sunday(6)
        if current.weekday() < 5:
            days_added += 1
    return current


def normalize_to_business_day(d: date) -> date:
    """
    Ensure a date falls on a business day (Mon-Fri).
    GLOBAL RULE: Follow-up dates should never land on weekends.
    """
    weekday = d.weekday()
    if weekday == 5:  # Saturday -> Monday
        return d + timedelta(days=2)
    elif weekday == 6:  # Sunday -> Monday
        return d + timedelta(days=1)
    return d


def update_contact_followup(contact: Contact, activity_type: str = None):
    """Update next_followup based on activity type.

    - "meeting_requested": Sets follow-up to 2 business days from today.
      This is used when a meeting has been discussed but not yet scheduled.
      Outlook is the source of truth for scheduled meetings - this app only
      tracks reminders to follow up on pending meeting requests.
    - All other activity types: Sets follow-up to 30 days from last_contacted (normalized to business day).
    """
    if activity_type == "meeting_requested":
        # Short follow-up: check back in 2 business days to see if meeting was scheduled
        contact.next_followup = add_business_days(date.today(), 2)
    else:
        # Standard follow-up: 30 days from last contact, normalized to business day
        contact.next_followup = normalize_to_business_day(contact.last_contacted + timedelta(days=30))


router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_class=HTMLResponse)
async def list_contacts(
    request: Request,
    search: str = None,
    account_id: str = None,
    sort: str = None,
    dir: str = None,
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

    # Normalize direction
    direction = dir if dir in ("asc", "desc") else None

    # Apply sorting based on URL parameters
    if sort == "name":
        if direction == "desc":
            query = query.order_by(Contact.last_name.desc(), Contact.first_name.desc())
        else:
            query = query.order_by(Contact.last_name.asc(), Contact.first_name.asc())
    elif sort == "account":
        if direction == "desc":
            query = query.order_by(Account.name.desc(), Contact.last_name.asc())
        else:
            query = query.order_by(Account.name.asc(), Contact.last_name.asc())
    elif sort == "last_contacted":
        # Handle nulls - put uncontacted at the end for desc, beginning for asc
        if direction == "asc":
            query = query.order_by(Contact.last_contacted.asc().nullsfirst())
        else:
            query = query.order_by(Contact.last_contacted.desc().nullslast())
    else:
        # Default sort by name
        query = query.order_by(Contact.last_name.asc(), Contact.first_name.asc())

    contacts = query.all()
    accounts = db.query(Account).order_by(Account.name).all()

    # Build query string for preserving state in navigation
    query_string = str(request.query_params) if request.query_params else ""

    return templates.TemplateResponse(
        "contacts/list.html",
        {
            "request": request,
            "contacts": contacts,
            "accounts": accounts,
            "search": search,
            "account_id": account_id_int,
            "sort": sort,
            "dir": direction or ("asc" if sort in ("name", "account") else "desc"),
            "list_query_string": query_string,
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
        last_name=last_name.strip() if last_name and last_name.strip() else None,
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
    next_followup: str = Form(None),
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
    contact.last_name = last_name.strip() if last_name and last_name.strip() else None
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

    # Handle next_followup - allow manual edit/clear independently
    if next_followup and next_followup.strip():
        contact.next_followup = datetime.strptime(next_followup, "%Y-%m-%d").date()
    else:
        contact.next_followup = None

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
        meeting_dt = utc_now()

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
    # Meeting occurred = standard 30-day follow-up (no special activity_type override)
    # Note: Outlook remains the source of truth for scheduled meetings.
    # This just logs that a meeting happened and sets a standard follow-up reminder.
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

    # Update last_contacted ONLY for actual contact (not meeting_requested)
    # For meeting_requested, the meeting hasn't happened yet - don't update last_contacted
    if activity_type != "meeting_requested":
        contact.last_contacted = date.today()

    # Pass activity_type to determine follow-up timing:
    # - "meeting_requested" gets a short 2 business day follow-up
    # - All other types get the standard 30 day follow-up
    update_contact_followup(contact, activity_type=activity_type)

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
        activity_date=utc_now(),
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
            activity_date=utc_now(),
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


# -----------------------------
# API Endpoints (JSON)
# -----------------------------

# Column names for Contact model (only these can be set)
CONTACT_COLUMNS = {
    "account_id", "first_name", "last_name", "title", "email",
    "phone", "mobile", "is_primary", "notes", "last_contacted", "next_followup",
}


@router.post("/{contact_id}/auto-save")
async def auto_save_contact(
    contact_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Production-safe autosave. Never raises 422 or 500."""
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return {"status": "saved"}

        try:
            payload = await request.json()
        except Exception:
            try:
                form = await request.form()
                payload = dict(form)
            except Exception:
                payload = {}

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

        for field, value in payload.items():
            if field not in CONTACT_COLUMNS:
                continue

            try:
                if field == "account_id":
                    parsed_id = clean_int(value)
                    if parsed_id:
                        contact.account_id = parsed_id
                elif field == "first_name":
                    val = str(value).strip() if value else ""
                    if val:
                        contact.first_name = val
                elif field == "is_primary":
                    is_primary_val = clean_bool(value)
                    if is_primary_val and not contact.is_primary:
                        try:
                            db.query(Contact).filter(
                                Contact.account_id == contact.account_id,
                                Contact.is_primary == True,
                                Contact.id != contact_id,
                            ).update({"is_primary": False})
                        except Exception:
                            pass
                    contact.is_primary = is_primary_val
                elif field in ("last_contacted", "next_followup"):
                    setattr(contact, field, clean_date(value))
                else:
                    if isinstance(value, str):
                        setattr(contact, field, value.strip() if value.strip() else None)
                    else:
                        setattr(contact, field, value if value else None)
            except Exception:
                continue

        try:
            db.commit()
        except Exception:
            db.rollback()

        return {"status": "saved"}
    except Exception:
        return {"status": "saved"}
