"""
Today / This Week Route

Shows actionable items for today and the upcoming week:
- Opportunities needing follow-up (due today or overdue)
- Tasks due today or within next 7 days
- Opportunities with upcoming bid dates (next 7 days)
- Meetings pending (meeting_requested activities not yet due)
"""

from datetime import date, datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Opportunity, Task, Contact, Activity

router = APIRouter(tags=["today"])
templates = Jinja2Templates(directory="app/templates")


def add_business_days(start_date: date, num_days: int) -> date:
    """Add business days (Mon-Fri) to a date, skipping weekends."""
    current = start_date
    days_added = 0
    while days_added < num_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days_added += 1
    return current


def normalize_to_business_day(d: date) -> date:
    """
    Ensure a date falls on a business day (Mon-Fri).
    If the date is Saturday, move to Monday.
    If the date is Sunday, move to Monday.
    GLOBAL RULE: Follow-up dates should never land on weekends.
    """
    weekday = d.weekday()
    if weekday == 5:  # Saturday -> Monday
        return d + timedelta(days=2)
    elif weekday == 6:  # Sunday -> Monday
        return d + timedelta(days=1)
    return d


@router.post("/today/mark-meeting-occurred/{activity_id}")
async def mark_meeting_occurred(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db),
):
    """
    Quick action: Convert a "Meeting Requested" activity to "Meeting" (occurred).

    PURPOSE: One-click closure of the open loop when a meeting actually happens.

    BEHAVIOR:
    - Updates activity_type from "meeting_requested" to "meeting"
    - Updates activity_date to now (meeting occurred today)
    - Updates contact.last_contacted to today
    - Sets contact.next_followup to 30 days from today (normalized to business day)

    RETURNS: JSON for AJAX - no page reload needed.
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if activity.activity_type != "meeting_requested":
        return JSONResponse(
            {"success": False, "error": "Activity is not a meeting request"},
            status_code=400,
        )

    if not activity.contact_id:
        return JSONResponse(
            {"success": False, "error": "Activity has no associated contact"},
            status_code=400,
        )

    contact = db.query(Contact).filter(Contact.id == activity.contact_id).first()
    if not contact:
        return JSONResponse(
            {"success": False, "error": "Contact not found"},
            status_code=404,
        )

    # Update the activity: meeting_requested -> meeting
    activity.activity_type = "meeting"
    activity.activity_date = datetime.now()  # Meeting occurred today
    activity.subject = f"Meeting with {contact.full_name}"

    # Update the contact: standard post-meeting follow-up (30 days, normalized to business day)
    contact.last_contacted = date.today()
    contact.next_followup = normalize_to_business_day(date.today() + timedelta(days=30))

    db.commit()

    return JSONResponse({"success": True})


@router.get("/today", response_class=HTMLResponse)
async def today_page(request: Request, db: Session = Depends(get_db)):
    """Today / This Week page showing actionable items."""
    today = date.today()
    week_from_now = today + timedelta(days=7)

    # Opportunities with follow-ups due today or overdue (only open opportunities)
    # Eager load account for template rendering (opp.account.name)
    followup_opps = (
        db.query(Opportunity)
        .options(selectinload(Opportunity.account))
        .filter(
            Opportunity.next_followup <= today,
            Opportunity.stage.notin_(["Won", "Lost"]),
        )
        .order_by(Opportunity.next_followup)
        .all()
    )

    # Contacts with follow-ups due today or overdue
    # This includes contacts where "Meeting Requested" was logged (2 business day follow-up)
    # Note: Outlook is the source of truth for scheduled meetings - this app only tracks
    # reminders to follow up on pending meeting requests or other contact activities.
    followup_contacts = (
        db.query(Contact)
        .options(selectinload(Contact.account))
        .filter(Contact.next_followup <= today)
        .order_by(Contact.next_followup)
        .all()
    )

    # For contacts with follow-ups due, find which ones have a pending "meeting_requested" activity
    # This allows showing the "Mark as Meeting" button for quick closure
    contact_meeting_activities = {}
    if followup_contacts:
        contact_ids = [c.id for c in followup_contacts]
        meeting_activities = (
            db.query(Activity)
            .filter(
                Activity.activity_type == "meeting_requested",
                Activity.contact_id.in_(contact_ids),
            )
            .all()
        )
        # Map contact_id -> most recent meeting_requested activity
        for activity in meeting_activities:
            existing = contact_meeting_activities.get(activity.contact_id)
            if not existing or activity.activity_date > existing.activity_date:
                contact_meeting_activities[activity.contact_id] = activity

    # Tasks due today or within next 7 days (only open tasks)
    # Eager load opportunity for template rendering (task.opportunity.name)
    upcoming_tasks = (
        db.query(Task)
        .options(selectinload(Task.opportunity))
        .filter(Task.due_date <= week_from_now, Task.status == "Open")
        .order_by(Task.due_date, Task.priority.desc())
        .all()
    )

    # Opportunities with bid dates in next 7 days (only open opportunities)
    # Eager load account for template rendering (opp.account.name)
    upcoming_bids = (
        db.query(Opportunity)
        .options(selectinload(Opportunity.account))
        .filter(
            Opportunity.bid_date >= today,
            Opportunity.bid_date <= week_from_now,
            Opportunity.stage.notin_(["Won", "Lost"]),
        )
        .order_by(Opportunity.bid_date)
        .all()
    )

    # Meetings Pending: "Meeting Requested" activities where follow-up is NOT yet due
    # PURPOSE: Show open loops BEFORE they become actionable - for visibility and confidence.
    # These are meetings that were discussed but not yet scheduled.
    # IMPORTANT: Query by Activity.id to avoid duplicates. Each row = one Activity.
    #
    # TWO-STEP APPROACH to prevent duplicates:
    # Step 1: Get unique Activity IDs using a clean subquery (no eager loading interference)
    # Step 2: Load those activities with eager loading for template rendering

    # Step 1: Subquery to get Activity IDs that match our criteria
    pending_activity_ids_query = (
        select(Activity.id)
        .join(Contact, Activity.contact_id == Contact.id)
        .where(
            Activity.activity_type == "meeting_requested",
            Activity.contact_id.isnot(None),
            Contact.next_followup > today,
        )
    )
    pending_activity_ids = [row[0] for row in db.execute(pending_activity_ids_query).fetchall()]

    # Step 2: Load activities by ID with eager loading (no joins = no duplication)
    if pending_activity_ids:
        meetings_pending = (
            db.query(Activity)
            .options(selectinload(Activity.contact).selectinload(Contact.account))
            .filter(Activity.id.in_(pending_activity_ids))
            .all()
        )
        # Sort in Python: by contact.next_followup, then by activity.id
        meetings_pending.sort(key=lambda a: (a.contact.next_followup if a.contact else date.max, a.id))
    else:
        meetings_pending = []

    return templates.TemplateResponse(
        "today/index.html",
        {
            "request": request,
            "today": today,
            "followup_opps": followup_opps,
            "followup_contacts": followup_contacts,
            "contact_meeting_activities": contact_meeting_activities,  # Map contact_id -> meeting_requested Activity
            "upcoming_tasks": upcoming_tasks,
            "upcoming_bids": upcoming_bids,
            "meetings_pending": meetings_pending,
        },
    )
