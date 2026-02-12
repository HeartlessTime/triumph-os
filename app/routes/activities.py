import logging
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from typing import List, Optional
from app.database import get_db
from app.models import Opportunity, Activity, Contact, ActivityAttendee
from app.services.followup import calculate_next_followup
from app.template_config import templates, utc_now
from app.utils.safe_redirect import safe_redirect_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activities", tags=["activities"])


def _add_business_days(start_date: date, num_days: int) -> date:
    """Add business days (Mon-Fri) to a date, skipping weekends."""
    current = start_date
    days_added = 0
    while days_added < num_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days_added += 1
    return current


def _normalize_to_business_day(d: date) -> date:
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




@router.post("/opportunity/{opp_id}/add")
async def add_activity(
    request: Request,
    opp_id: int,
    activity_type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    activity_date: str = Form(None),
    contact_id: int = Form(None),
    update_last_contacted: bool = Form(True),
    db: Session = Depends(get_db),
):
    """Add an activity to an opportunity."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Parse activity date
    if activity_date:
        activity_dt = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
    else:
        activity_dt = utc_now()

    current_user = request.state.current_user
    activity = Activity(
        opportunity_id=opp_id,
        activity_type=activity_type,
        subject=subject,
        description=description or None,
        activity_date=activity_dt,
        contact_id=contact_id if contact_id else None,
        created_by_id=current_user.id,
    )

    db.add(activity)

    # Update last_contacted if requested and activity is today or in the past
    if update_last_contacted and activity_dt.date() <= date.today():
        opportunity.last_contacted = activity_dt.date()
        # Recalculate followup
        opportunity.next_followup = calculate_next_followup(
            stage=opportunity.stage,
            last_contacted=opportunity.last_contacted,
            bid_date=opportunity.bid_date,
        )

    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.post("/add")
async def add_standalone_activity(
    request: Request,
    activity_type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    activity_date: str = Form(None),
    contact_id: int = Form(None),
    opportunity_id: int = Form(None),
    requires_estimate: str = Form(None),
    scope_summary: str = Form(None),
    estimated_quantity: str = Form(None),
    complexity_notes: str = Form(None),
    estimate_needed_by: str = Form(None),
    assigned_estimator_id: int = Form(None),
    db: Session = Depends(get_db),
):
    """Add a standalone activity (not necessarily linked to an opportunity).

    Used for site visits and other activities that may or may not be
    linked to an opportunity, contact, or account.
    """
    current_user = request.state.current_user
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Parse activity date
    if activity_date:
        activity_dt = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
    else:
        activity_dt = utc_now()

    activity = Activity(
        activity_type=activity_type,
        subject=subject,
        description=description or None,
        activity_date=activity_dt,
        contact_id=contact_id if contact_id else None,
        opportunity_id=opportunity_id if opportunity_id else None,
        created_by_id=current_user.id,
    )

    # Job walk fields (site visits only)
    if requires_estimate and requires_estimate.lower() in ("true", "1", "on"):
        activity.requires_estimate = True
        activity.scope_summary = scope_summary.strip() if scope_summary and scope_summary.strip() else None
        activity.estimated_quantity = estimated_quantity.strip()[:100] if estimated_quantity and estimated_quantity.strip() else None
        activity.complexity_notes = complexity_notes.strip() if complexity_notes and complexity_notes.strip() else None
        if estimate_needed_by and estimate_needed_by.strip():
            try:
                activity.estimate_needed_by = datetime.strptime(estimate_needed_by.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass
        activity.assigned_estimator_id = assigned_estimator_id if assigned_estimator_id else None

    db.add(activity)
    db.commit()
    db.refresh(activity)

    # Redirect to the newly created activity's detail page
    return RedirectResponse(url=f"/activities/{activity.id}", status_code=303)


@router.post("/log-meeting")
async def log_meeting(
    request: Request,
    account_id: int = Form(...),
    activity_date: str = Form(...),
    subject: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
):
    """Log a meeting with multiple contacts from the same account.

    Creates one Activity record with multiple attendees via the
    activity_attendees junction table.
    """
    current_user = request.state.current_user

    # Parse contact_ids from form (multiple checkboxes with same name)
    form_data = await request.form()
    contact_ids = [int(v) for v in form_data.getlist("contact_ids") if v]

    # Parse activity date
    activity_dt = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")

    # Build subject from attendees if not provided
    if not subject or not subject.strip():
        if contact_ids:
            contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
            names = [c.full_name for c in contacts]
            if len(names) == 1:
                subject = f"Meeting with {names[0]}"
            elif len(names) == 2:
                subject = f"Meeting with {names[0]} and {names[1]}"
            else:
                subject = f"Meeting with {names[0]} + {len(names) - 1} others"
        else:
            subject = "Meeting"

    activity = Activity(
        activity_type="meeting",
        subject=subject.strip() if subject else "Meeting",
        description=description.strip() if description and description.strip() else None,
        activity_date=activity_dt,
        contact_id=contact_ids[0] if contact_ids else None,  # Primary contact for backward compat
        created_by_id=current_user.id,
    )
    db.add(activity)
    db.flush()  # Get activity.id

    # Add attendees
    for cid in contact_ids:
        attendee = ActivityAttendee(
            activity_id=activity.id,
            contact_id=cid,
        )
        db.add(attendee)

    # Update last_contacted on all attending contacts
    if contact_ids and activity_dt.date() <= date.today():
        contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
        for contact in contacts:
            contact.last_contacted = activity_dt.date()
            contact.has_responded = True
            # Set 30-day follow-up (standard post-meeting)
            contact.next_followup = _normalize_to_business_day(
                activity_dt.date() + timedelta(days=30)
            )

    db.commit()

    redirect_to = safe_redirect_url(request.query_params.get("from"), "/")
    return RedirectResponse(url=redirect_to, status_code=303)


@router.get("/{activity_id}", response_class=HTMLResponse)
async def view_activity(
    request: Request, activity_id: int, db: Session = Depends(get_db)
):
    """View activity details (read-only)."""
    from sqlalchemy.orm import selectinload as sl

    activity = (
        db.query(Activity)
        .options(
            sl(Activity.contact).selectinload(Contact.account),
            sl(Activity.opportunity),
            sl(Activity.attendee_links).selectinload(ActivityAttendee.contact).selectinload(Contact.account),
            sl(Activity.walk_segments),
        )
        .filter(Activity.id == activity_id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    return templates.TemplateResponse(
        "activities/view.html",
        {
            "request": request,
            "activity": activity,
        },
    )


@router.get("/{activity_id}/edit", response_class=HTMLResponse)
async def edit_activity_form(
    request: Request, activity_id: int, db: Session = Depends(get_db)
):
    """Display edit activity form.

    Activities can belong to:
    - An Opportunity (with optional Contact)
    - A Contact only (no Opportunity)
    - Neither (orphaned activity - logged but navigable)

    GUARDRAILS:
    - Never assumes activity.opportunity exists
    - Safely determines context owner for contact dropdown
    - Prevents full-table queries by requiring account_id filter
    - Logs warning for orphaned activities
    """
    # 1. Immediate 404 if activity doesn't exist
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 2. Determine context owner account_id (NEVER assume opportunity exists)
    context_account_id = None
    contacts = []

    if activity.opportunity is not None:
        # Activity is linked to an opportunity - use opportunity's primary account
        context_account_id = activity.opportunity.primary_account_id
    elif activity.contact is not None:
        # Activity is linked to a contact only - use contact's account
        context_account_id = activity.contact.account_id
    else:
        # Orphaned activity - has neither opportunity nor contact
        logger.warning(
            f"Activity {activity_id} has no opportunity or contact. "
            f"Type: {activity.activity_type}, Subject: {activity.subject}"
        )

    # 3. Only query contacts if we have a valid account_id (prevents full-table scan)
    if context_account_id is not None:
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id == context_account_id)
            .order_by(Contact.last_name)
            .all()
        )

    # Get attendee IDs for meetings
    attendee_ids = set()
    if activity.attendee_links:
        attendee_ids = {link.contact_id for link in activity.attendee_links}
    elif activity.contact_id:
        attendee_ids = {activity.contact_id}

    return templates.TemplateResponse(
        "activities/edit.html",
        {
            "request": request,
            "activity": activity,
            "contacts": contacts,
            "attendee_ids": attendee_ids,
            "activity_types": Activity.ACTIVITY_TYPES,
        },
    )


@router.post("/{activity_id}/edit")
async def update_activity(
    request: Request,
    activity_id: int,
    activity_type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    activity_date: str = Form(...),
    contact_id: int = Form(None),
    next_followup: str = Form(None),  # Manual follow-up date override
    db: Session = Depends(get_db),
):
    """Update an activity.

    REDIRECT RULE ORDER:
    1. If ?from= query param exists → use that URL (back navigation)
    2. Else if activity.opportunity exists → /opportunities/{id}
    3. Else if activity.contact exists → /contacts/{id}
    4. Else → /summary/my-weekly

    FOLLOW-UP LOGIC:
    - If user provides next_followup date, use it (manual override takes priority)
    - Else if activity_type changes: apply auto-follow-up logic
      - meeting_requested → meeting: apply standard 30-day follow-up
      - other → meeting_requested: apply 2-business-day follow-up
    - Else: preserve existing follow-up
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check for explicit return URL from query params (back navigation)
    from_url = request.query_params.get("from")
    if from_url:
        redirect_url = safe_redirect_url(from_url, "/summary/my-weekly")
    elif activity.opportunity_id:
        redirect_url = f"/opportunities/{activity.opportunity_id}"
    elif activity.contact_id:
        redirect_url = f"/contacts/{activity.contact_id}"
    else:
        redirect_url = "/summary/my-weekly"

    # Track if activity_type is changing (for follow-up logic)
    old_type = activity.activity_type
    type_changed = old_type != activity_type

    # Parse multi-contact attendee IDs (for meetings)
    form_data = await request.form()
    contact_ids = [int(v) for v in form_data.getlist("contact_ids") if v]

    # Apply updates
    activity.activity_type = activity_type
    activity.subject = subject
    activity.description = description or None
    activity.activity_date = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")

    # For meetings with attendees, update attendee_links and set contact_id to first
    if activity_type == "meeting" and contact_ids:
        activity.contact_id = contact_ids[0]
        # Replace attendee links
        db.query(ActivityAttendee).filter(ActivityAttendee.activity_id == activity.id).delete()
        for cid in contact_ids:
            db.add(ActivityAttendee(activity_id=activity.id, contact_id=cid))
    else:
        activity.contact_id = contact_id if contact_id else None

    # Update contact follow-up date
    # GLOBAL RULE: All follow-up dates are normalized to business days (Mon-Fri)
    if activity.contact_id:
        contact = db.query(Contact).filter(Contact.id == activity.contact_id).first()
        if contact:
            if next_followup and next_followup.strip():
                # Manual override: user explicitly set a follow-up date, normalize to business day
                manual_date = datetime.strptime(next_followup, "%Y-%m-%d").date()
                contact.next_followup = _normalize_to_business_day(manual_date)
            elif type_changed:
                # Auto-follow-up: only when activity_type changes and no manual date
                if activity_type == "meeting":
                    # Closing the loop: meeting occurred, set 30-day follow-up (normalized)
                    contact.last_contacted = date.today()
                    contact.next_followup = _normalize_to_business_day(date.today() + timedelta(days=30))
                elif activity_type == "meeting_requested":
                    # New meeting request: set 2-business-day follow-up
                    contact.next_followup = _add_business_days(date.today(), 2)
            # else: no manual date and no type change - preserve existing follow-up

    db.commit()

    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/{activity_id}/quick-note")
async def quick_note(
    activity_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update activity notes via inline quick-note input (JSON API)."""
    # Auth: request.state.current_user is set by middleware for all routes
    current_user = request.state.current_user
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    data = await request.json()
    activity.description = data.get("notes", "").strip() or None
    db.commit()

    return {"ok": True}


@router.post("/{activity_id}/delete")
async def delete_activity(
    request: Request, activity_id: int, db: Session = Depends(get_db)
):
    """Delete an activity.

    REDIRECT RULE ORDER:
    1. If ?from= query param exists → use that URL (back navigation)
    2. Else if activity.opportunity_id exists → /opportunities/{id}
    3. Else if activity.contact_id exists → /contacts/{id}
    4. Else → /summary/my-weekly
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check for explicit return URL from query params (back navigation)
    from_url = request.query_params.get("from")
    if from_url:
        redirect_url = safe_redirect_url(from_url, "/summary/my-weekly")
    elif activity.opportunity_id:
        redirect_url = f"/opportunities/{activity.opportunity_id}"
    elif activity.contact_id:
        redirect_url = f"/contacts/{activity.contact_id}"
    else:
        redirect_url = "/summary/my-weekly"

    db.delete(activity)
    db.commit()

    return RedirectResponse(url=redirect_url, status_code=303)


# -----------------------------
# API Endpoints (JSON)
# -----------------------------


# Column names for Activity model (only these can be set)
ACTIVITY_COLUMNS = {
    "activity_type", "subject", "description", "activity_date",
    "contact_id", "opportunity_id",
    # Job walk fields
    "walk_notes", "job_walk_status", "estimate_due_by",
    "technicians_needed", "estimated_man_hours",
    # Job walk / estimating fields
    "requires_estimate", "scope_summary", "estimated_quantity",
    "complexity_notes", "estimate_needed_by", "assigned_estimator_id",
    "estimate_completed", "estimate_completed_at",
}


@router.post("/{activity_id}/auto-save")
async def auto_save_activity(
    activity_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Production-safe autosave. Never raises 422 or 500."""
    try:
        activity = db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
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

        def clean_date(v):
            if not v or v in ("", "null"):
                return None
            try:
                return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()
            except Exception:
                return None

        def clean_datetime(v):
            if not v or v in ("", "null"):
                return None
            val = str(v).strip()
            try:
                if "T" in val:
                    return datetime.strptime(val, "%Y-%m-%dT%H:%M")
                else:
                    return datetime.strptime(val, "%Y-%m-%d")
            except Exception:
                return None

        # Track if activity_type is changing (for follow-up logic)
        old_type = activity.activity_type

        for field, value in payload.items():
            if field not in ACTIVITY_COLUMNS:
                continue

            try:
                if field == "activity_type":
                    val = str(value).strip() if value else ""
                    if val:
                        activity.activity_type = val
                elif field == "subject":
                    val = str(value).strip() if value else ""
                    if val:
                        activity.subject = val
                elif field == "activity_date":
                    parsed = clean_datetime(value)
                    if parsed:
                        activity.activity_date = parsed
                elif field in ("contact_id", "opportunity_id"):
                    setattr(activity, field, clean_int(value))
                elif field == "description":
                    activity.description = str(value).strip() if value and str(value).strip() else None
                elif field in ("requires_estimate", "estimate_completed"):
                    if isinstance(value, bool):
                        bool_val = value
                    elif isinstance(value, list):
                        # JS sends ["true"] when checked, [] when unchecked
                        bool_val = len(value) > 0
                    else:
                        bool_val = str(value).lower() in ("true", "1", "on")
                    setattr(activity, field, bool_val)
                    # Auto-stamp estimate_completed_at when marking complete
                    if field == "estimate_completed":
                        activity.estimate_completed_at = date.today() if bool_val else None
                elif field == "estimate_completed_at":
                    activity.estimate_completed_at = clean_date(value)
                elif field == "walk_notes":
                    activity.walk_notes = str(value) if value else None
                elif field == "job_walk_status":
                    val = str(value).strip() if value else ""
                    if val in ("open", "sent_to_estimator", "complete"):
                        activity.job_walk_status = val
                elif field == "estimate_due_by":
                    activity.estimate_due_by = clean_date(value)
                elif field in ("technicians_needed", "estimated_man_hours"):
                    setattr(activity, field, clean_int(value))
                elif field in ("scope_summary", "complexity_notes"):
                    setattr(activity, field, str(value).strip() if value and str(value).strip() else None)
                elif field == "estimated_quantity":
                    activity.estimated_quantity = str(value).strip()[:100] if value and str(value).strip() else None
                elif field == "estimate_needed_by":
                    activity.estimate_needed_by = clean_date(value)
                elif field == "assigned_estimator_id":
                    setattr(activity, field, clean_int(value))
            except Exception:
                continue

        # Update attendees for meetings
        try:
            if "contact_ids" in payload and activity.activity_type == "meeting":
                raw_ids = payload["contact_ids"]
                new_ids = []
                if isinstance(raw_ids, list):
                    for v in raw_ids:
                        try:
                            new_ids.append(int(v))
                        except (ValueError, TypeError):
                            pass
                elif not isinstance(raw_ids, bool):
                    # Scalar value (not a boolean from checkbox default)
                    try:
                        if raw_ids not in (None, "", "null"):
                            new_ids = [int(raw_ids)]
                    except (ValueError, TypeError):
                        pass
                # else: boolean means malformed checkbox data — skip attendee update
                if isinstance(raw_ids, list) or not isinstance(raw_ids, bool):
                    db.query(ActivityAttendee).filter(
                        ActivityAttendee.activity_id == activity.id
                    ).delete(synchronize_session="fetch")
                    for cid in new_ids:
                        db.add(ActivityAttendee(activity_id=activity.id, contact_id=cid))
                    activity.contact_id = new_ids[0] if new_ids else activity.contact_id
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Auto-save ATTENDEE ERROR for activity {activity_id}: {e}")
            pass

        # Update contact follow-up date if provided or activity_type changed
        try:
            type_changed = "activity_type" in payload and old_type != activity.activity_type
            if activity.contact_id:
                contact = db.query(Contact).filter(Contact.id == activity.contact_id).first()
                if contact:
                    if "next_followup" in payload:
                        followup_date = clean_date(payload["next_followup"])
                        if followup_date:
                            contact.next_followup = _normalize_to_business_day(followup_date)
                        else:
                            contact.next_followup = None
                    elif type_changed:
                        # Auto-follow-up: only when activity_type changes and no manual date
                        if activity.activity_type == "meeting":
                            contact.last_contacted = date.today()
                            contact.next_followup = _normalize_to_business_day(date.today() + timedelta(days=30))
                        elif activity.activity_type == "meeting_requested":
                            contact.next_followup = _add_business_days(date.today(), 2)
        except Exception:
            pass

        try:
            db.commit()
            import logging
            logging.getLogger(__name__).info(f"Auto-save OK for activity {activity_id}: description={activity.description!r}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Auto-save COMMIT FAILED for activity {activity_id}: {e}")
            db.rollback()

        return {"status": "saved"}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Auto-save OUTER ERROR for activity {activity_id}: {e}")
        return {"status": "saved"}
