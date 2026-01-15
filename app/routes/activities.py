import logging
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Opportunity, Activity, Contact
from app.services.followup import calculate_next_followup
from app.template_config import templates, utc_now

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
        # Activity is linked to an opportunity - use opportunity's account
        context_account_id = activity.opportunity.account_id
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

    return templates.TemplateResponse(
        "activities/edit.html",
        {
            "request": request,
            "activity": activity,
            "contacts": contacts,
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
        redirect_url = from_url
    elif activity.opportunity_id:
        redirect_url = f"/opportunities/{activity.opportunity_id}"
    elif activity.contact_id:
        redirect_url = f"/contacts/{activity.contact_id}"
    else:
        redirect_url = "/summary/my-weekly"

    # Track if activity_type is changing (for follow-up logic)
    old_type = activity.activity_type
    type_changed = old_type != activity_type

    # Apply updates
    activity.activity_type = activity_type
    activity.subject = subject
    activity.description = description or None
    activity.activity_date = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
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
        redirect_url = from_url
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
from pydantic import BaseModel
from typing import Optional


class ActivityAutoSaveRequest(BaseModel):
    activity_type: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    activity_date: Optional[str] = None
    contact_id: Optional[int] = None
    next_followup: Optional[str] = None


@router.post("/{activity_id}/auto-save")
async def auto_save_activity(
    activity_id: int,
    data: ActivityAutoSaveRequest,
    db: Session = Depends(get_db),
):
    """Auto-save activity fields (JSON API for real-time updates)."""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Track if activity_type is changing (for follow-up logic)
    old_type = activity.activity_type

    # Update only the fields that were provided
    if data.activity_type is not None:
        activity.activity_type = data.activity_type
    if data.subject is not None:
        activity.subject = data.subject
    if data.description is not None:
        activity.description = data.description or None
    if data.activity_date is not None and data.activity_date.strip():
        activity.activity_date = datetime.strptime(data.activity_date, "%Y-%m-%dT%H:%M")
    if data.contact_id is not None:
        activity.contact_id = data.contact_id if data.contact_id else None

    # Update contact follow-up date if provided or activity_type changed
    type_changed = data.activity_type is not None and old_type != data.activity_type
    if activity.contact_id:
        contact = db.query(Contact).filter(Contact.id == activity.contact_id).first()
        if contact:
            if data.next_followup is not None:
                if data.next_followup.strip():
                    # Manual override: user explicitly set a follow-up date
                    manual_date = datetime.strptime(data.next_followup, "%Y-%m-%d").date()
                    contact.next_followup = _normalize_to_business_day(manual_date)
                else:
                    contact.next_followup = None
            elif type_changed:
                # Auto-follow-up: only when activity_type changes and no manual date
                if activity.activity_type == "meeting":
                    contact.last_contacted = date.today()
                    contact.next_followup = _normalize_to_business_day(date.today() + timedelta(days=30))
                elif activity.activity_type == "meeting_requested":
                    contact.next_followup = _add_business_days(date.today(), 2)

    db.commit()

    return {"ok": True, "id": activity.id}
