"""
Weekly Summary Router

Provides weekly summary pages:
- Team Weekly Summary: Shows ALL team activity (no user filter)
- My Weekly Summary: Shows only the current user's activity
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func  # kept for potential future use

from app.database import get_db
from app.models import Account, Contact, Opportunity, Activity, Task, WeeklySummaryNote, User

router = APIRouter(prefix="/summary", tags=["summary"])
templates = Jinja2Templates(directory="app/templates")



def get_week_start_monday(for_date: Optional[date] = None) -> date:
    """Get the Monday of the week for a given date (or current week if None)."""
    target = for_date or date.today()
    # weekday() returns 0 for Monday, 6 for Sunday
    days_since_monday = target.weekday()
    return target - timedelta(days=days_since_monday)


def get_week_boundaries_for_week(week_start: date):
    """Get start (Monday) and end (Sunday) dates for a given week."""
    return week_start, week_start + timedelta(days=6)


def load_notes_for_week(db: Session, week_start: date, user_id: Optional[int] = None) -> Dict[str, str]:
    """
    Load all notes for a given week, keyed by section.

    Args:
        db: Database session
        week_start: Monday of the week
        user_id: None for team notes, user's ID for personal notes
    """
    query = db.query(WeeklySummaryNote).filter(
        WeeklySummaryNote.week_start == week_start
    )

    if user_id is None:
        # Team notes: user_id IS NULL
        query = query.filter(WeeklySummaryNote.user_id.is_(None))
    else:
        # Personal notes: user_id = specific user
        query = query.filter(WeeklySummaryNote.user_id == user_id)

    notes = query.all()
    return {note.section: note.notes or "" for note in notes}


@router.get("/weekly", response_class=HTMLResponse)
async def weekly_summary(
    request: Request,
    week_start: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Weekly summary page showing work completed in a specific week.

    Query params:
        week_start: Monday of the week to display (YYYY-MM-DD). Defaults to current week.
    """
    # Determine the week to display
    if week_start:
        # Normalize to Monday of that week
        week_start = get_week_start_monday(week_start)
    else:
        week_start = get_week_start_monday()

    start_date, end_date = get_week_boundaries_for_week(week_start)
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Calculate previous and next week
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    current_week = get_week_start_monday()
    is_current_week = (week_start == current_week)

    # ----------------------------
    # TEAM-WIDE DATA (No user filter)
    # ----------------------------
    # Team summary shows ALL activities from all users

    # ----------------------------
    # MASTER ACTIVITY QUERY (Team-wide)
    # Eager load contact and opportunity to avoid N+1 in templates
    # ----------------------------
    activities_logged = db.query(Activity).options(
        selectinload(Activity.contact).selectinload(Contact.account),
        selectinload(Activity.opportunity)
    ).filter(
        Activity.activity_date >= start_datetime,
        Activity.activity_date <= end_datetime
    ).order_by(Activity.activity_date.desc()).all()
    activities_logged_count = len(activities_logged)

    # ----------------------------
    # 1) EXECUTIVE SUMMARY COUNTS (Team-wide)
    # ----------------------------

    # Contacts logged - count distinct contacts from ALL activities
    contacts_with_activity = [a for a in activities_logged if a.contact_id is not None]
    contacts_logged_ids = list(set(a.contact_id for a in contacts_with_activity))
    contacts_logged_count = len(contacts_logged_ids)

    # Opportunities touched - count distinct opportunities from ALL activities
    opps_with_activity = [a for a in activities_logged if a.opportunity_id is not None]
    opportunities_touched_ids = list(set(a.opportunity_id for a in opps_with_activity))
    opportunities_touched_count = len(opportunities_touched_ids)

    # Fetch actual opportunity objects for display
    # Eager load account for template rendering
    if opportunities_touched_ids:
        opportunities_touched = db.query(Opportunity).options(
            selectinload(Opportunity.account)
        ).filter(
            Opportunity.id.in_(opportunities_touched_ids)
        ).order_by(Opportunity.updated_at.desc()).all()
    else:
        opportunities_touched = []

    # New accounts created (team-wide)
    new_accounts = db.query(Account).filter(
        Account.created_at >= start_datetime,
        Account.created_at <= end_datetime
    ).order_by(Account.created_at.desc()).all()
    new_accounts_count = len(new_accounts)

    # New contacts (team-wide) - eager load account for template
    new_contacts = db.query(Contact).options(
        selectinload(Contact.account)
    ).filter(
        Contact.created_at >= start_datetime,
        Contact.created_at <= end_datetime
    ).order_by(Contact.created_at.desc()).all()
    new_contacts_count = len(new_contacts)

    # New opportunities created (team-wide) - no relationships accessed in template
    new_opportunities = db.query(Opportunity).filter(
        Opportunity.created_at >= start_datetime,
        Opportunity.created_at <= end_datetime
    ).order_by(Opportunity.created_at.desc()).all()
    new_opportunities_count = len(new_opportunities)

    # Tasks completed - all tasks completed during this week (assignment-agnostic)
    # Note: Task completion is tracked via status field, using updated_at as completion date
    # Eager load opportunity for template rendering
    tasks_completed = db.query(Task).options(
        selectinload(Task.opportunity)
    ).filter(
        Task.status == 'Completed',
        Task.updated_at >= start_datetime,
        Task.updated_at <= end_datetime
    ).order_by(Task.updated_at.desc()).all()
    tasks_completed_count = len(tasks_completed)

    # ----------------------------
    # 2) OUTREACH & FOLLOW-UPS (Derived from Activities)
    # ----------------------------
    # Filter activities by outreach types: call, meeting, email, site_visit
    outreach_types = ['call', 'meeting', 'email', 'site_visit']
    outreach_activities = [a for a in activities_logged if a.activity_type in outreach_types]

    # Get unique contacts from outreach activities - eager load account for template
    outreach_contact_ids = list(set(a.contact_id for a in outreach_activities if a.contact_id))
    if outreach_contact_ids:
        outreach_contacts = db.query(Contact).options(
            selectinload(Contact.account)
        ).filter(
            Contact.id.in_(outreach_contact_ids)
        ).all()
    else:
        outreach_contacts = []

    # ----------------------------
    # 3) PIPELINE MOVEMENT (Derived from Activities)
    # ----------------------------
    # Stage changes are logged as 'note' activities with "Stage changed" in subject
    # Eager load account for template rendering
    pipeline_activities = [a for a in activities_logged if 'Stage changed' in (a.subject or '')]
    pipeline_opp_ids = list(set(a.opportunity_id for a in pipeline_activities if a.opportunity_id))
    if pipeline_opp_ids:
        pipeline_changes = db.query(Opportunity).options(
            selectinload(Opportunity.account)
        ).filter(
            Opportunity.id.in_(pipeline_opp_ids)
        ).order_by(Opportunity.updated_at.desc()).all()
    else:
        pipeline_changes = []

    # ----------------------------
    # 4) TASKS COMPLETED
    # ----------------------------
    # Already fetched above as tasks_completed

    # ----------------------------
    # 5) NEW RECORDS CREATED
    # ----------------------------
    # Already fetched: new_accounts, new_contacts, new_opportunities

    # ----------------------------
    # 6) RECENT ACTIVITY TIMELINE
    # ----------------------------
    # Already fetched as activities_logged

    # ----------------------------
    # GENERATE SUMMARY SENTENCE (Team-wide language)
    # ----------------------------
    summary_parts = []
    if contacts_logged_count > 0:
        summary_parts.append(f"{contacts_logged_count} contact{'s' if contacts_logged_count != 1 else ''} logged")
    if activities_logged_count > 0:
        summary_parts.append(f"{activities_logged_count} activit{'ies' if activities_logged_count != 1 else 'y'} recorded")
    if tasks_completed_count > 0:
        summary_parts.append(f"{tasks_completed_count} task{'s' if tasks_completed_count != 1 else ''} completed")
    if new_opportunities_count > 0:
        summary_parts.append(f"{new_opportunities_count} new opportunit{'ies' if new_opportunities_count != 1 else 'y'}")

    week_label = "This week" if is_current_week else f"Week of {start_date.strftime('%b %d')}"
    if summary_parts:
        summary_sentence = f"{week_label} the team logged " + ", ".join(summary_parts) + "."
    else:
        summary_sentence = f"No team activity recorded for {week_label.lower()}."

    # ----------------------------
    # LOAD NOTES FOR THIS WEEK (Team notes: user_id = NULL)
    # ----------------------------
    section_notes = load_notes_for_week(db, week_start, user_id=None)

    return templates.TemplateResponse("summary/weekly.html", {
        "request": request,
        "start_date": start_date,
        "end_date": end_date,
        "week_start": week_start,
        "prev_week": prev_week,
        "next_week": next_week,
        "is_current_week": is_current_week,
        "summary_sentence": summary_sentence,
        # Counts
        "contacts_logged_count": contacts_logged_count,
        "new_contacts_count": new_contacts_count,
        "new_accounts_count": new_accounts_count,
        "opportunities_touched_count": opportunities_touched_count,
        "new_opportunities_count": new_opportunities_count,
        "tasks_completed_count": tasks_completed_count,
        "activities_logged_count": activities_logged_count,
        # Lists
        "outreach_contacts": outreach_contacts,
        "pipeline_changes": pipeline_changes,
        "tasks_completed": tasks_completed,
        "new_accounts": new_accounts,
        "new_contacts": new_contacts,
        "new_opportunities": new_opportunities,
        "activities_logged": activities_logged,
        # Notes
        "section_notes": section_notes,
    })


@router.post("/weekly/notes")
async def save_weekly_note(
    request: Request,
    week_start: date = Form(...),
    section: str = Form(...),
    notes: str = Form(""),
    note_type: str = Form("team"),
    db: Session = Depends(get_db)
):
    """
    Save or update a note for a specific section and week.

    Form fields:
        week_start: The Monday of the week (YYYY-MM-DD)
        section: One of 'outreach', 'pipeline', 'tasks', 'new_records', 'other'
        notes: The note content (can be empty)
        note_type: 'team' for team notes (user_id=NULL), 'personal' for user-specific notes
    """
    # Determine redirect URL based on note type
    if note_type == "personal":
        redirect_url = f"/summary/my-weekly?week_start={week_start}"
        current_user = request.state.current_user
        user_id = current_user.id
    else:
        redirect_url = f"/summary/weekly?week_start={week_start}"
        user_id = None

    # Validate section
    if section not in WeeklySummaryNote.SECTIONS:
        return RedirectResponse(url=redirect_url, status_code=303)

    # Find existing note or create new one
    # Query must match week_start + section + user_id (including NULL)
    query = db.query(WeeklySummaryNote).filter(
        WeeklySummaryNote.week_start == week_start,
        WeeklySummaryNote.section == section
    )
    if user_id is None:
        query = query.filter(WeeklySummaryNote.user_id.is_(None))
    else:
        query = query.filter(WeeklySummaryNote.user_id == user_id)

    existing = query.first()

    if existing:
        existing.notes = notes
        existing.updated_at = datetime.utcnow()
    else:
        new_note = WeeklySummaryNote(
            week_start=week_start,
            section=section,
            user_id=user_id,
            notes=notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_note)

    db.commit()

    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/my-weekly", response_class=HTMLResponse)
async def my_weekly_summary(
    request: Request,
    week_start: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Personal weekly summary showing work the current user completed.

    Mirrors the Team Weekly Summary structure but filters ALL data to the current user:
    - Tasks completed BY this user (completed_by_id)
    - Activities logged BY this user
    - Accounts/Contacts/Opportunities created BY this user
    - Pipeline changes caused BY this user
    """
    current_user = request.state.current_user
    user_id = current_user.id

    # Determine the week to display
    if week_start:
        week_start = get_week_start_monday(week_start)
    else:
        week_start = get_week_start_monday()

    start_date, end_date = get_week_boundaries_for_week(week_start)
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Calculate previous and next week
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    current_week_monday = get_week_start_monday()
    is_current_week = (week_start == current_week_monday)

    # ----------------------------
    # MASTER ACTIVITY QUERY (filtered to current user)
    # Eager load contact and opportunity to avoid N+1 in templates
    # ----------------------------
    activities_logged = db.query(Activity).options(
        selectinload(Activity.contact).selectinload(Contact.account),
        selectinload(Activity.opportunity)
    ).filter(
        Activity.created_by_id == user_id,
        Activity.activity_date >= start_datetime,
        Activity.activity_date <= end_datetime
    ).order_by(Activity.activity_date.desc()).all()
    activities_logged_count = len(activities_logged)

    # ----------------------------
    # EXECUTIVE SUMMARY COUNTS
    # ----------------------------

    # Contacts logged - distinct contacts from user's activities
    contacts_with_activity = [a for a in activities_logged if a.contact_id is not None]
    contacts_logged_ids = list(set(a.contact_id for a in contacts_with_activity))
    contacts_logged_count = len(contacts_logged_ids)

    # Opportunities touched - distinct opportunities from user's activities
    opps_with_activity = [a for a in activities_logged if a.opportunity_id is not None]
    opportunities_touched_ids = list(set(a.opportunity_id for a in opps_with_activity))
    opportunities_touched_count = len(opportunities_touched_ids)

    # Fetch actual opportunity objects for display - eager load account for template
    if opportunities_touched_ids:
        opportunities_touched = db.query(Opportunity).options(
            selectinload(Opportunity.account)
        ).filter(
            Opportunity.id.in_(opportunities_touched_ids)
        ).order_by(Opportunity.updated_at.desc()).all()
    else:
        opportunities_touched = []

    # New accounts created by this user
    new_accounts = db.query(Account).filter(
        Account.created_at >= start_datetime,
        Account.created_at <= end_datetime,
        Account.created_by_id == user_id
    ).order_by(Account.created_at.desc()).all()
    new_accounts_count = len(new_accounts)

    # New contacts - from accounts created by user or with activities
    user_account_ids = [acc.id for acc in new_accounts]
    if opportunities_touched_ids:
        touched_account_ids = [opp.account_id for opp in opportunities_touched]
        user_account_ids = list(set(user_account_ids + touched_account_ids))

    # Eager load account for template rendering
    if user_account_ids:
        new_contacts = db.query(Contact).options(
            selectinload(Contact.account)
        ).filter(
            Contact.created_at >= start_datetime,
            Contact.created_at <= end_datetime,
            Contact.account_id.in_(user_account_ids)
        ).order_by(Contact.created_at.desc()).all()
    else:
        new_contacts = []
    new_contacts_count = len(new_contacts)

    # New opportunities created by this user (owner)
    new_opportunities = db.query(Opportunity).filter(
        Opportunity.created_at >= start_datetime,
        Opportunity.created_at <= end_datetime,
        Opportunity.owner_id == user_id
    ).order_by(Opportunity.created_at.desc()).all()
    new_opportunities_count = len(new_opportunities)

    # Tasks completed BY this user (key difference from team summary)
    # Eager load opportunity for template rendering
    tasks_completed = db.query(Task).options(
        selectinload(Task.opportunity)
    ).filter(
        Task.completed_by_id == user_id,
        Task.status == 'Completed',
        Task.updated_at >= start_datetime,
        Task.updated_at <= end_datetime
    ).order_by(Task.updated_at.desc()).all()
    tasks_completed_count = len(tasks_completed)

    # ----------------------------
    # OUTREACH & FOLLOW-UPS
    # ----------------------------
    outreach_types = ['call', 'meeting', 'email', 'site_visit']
    outreach_activities = [a for a in activities_logged if a.activity_type in outreach_types]

    # Eager load account for template rendering
    outreach_contact_ids = list(set(a.contact_id for a in outreach_activities if a.contact_id))
    if outreach_contact_ids:
        outreach_contacts = db.query(Contact).options(
            selectinload(Contact.account)
        ).filter(
            Contact.id.in_(outreach_contact_ids)
        ).all()
    else:
        outreach_contacts = []

    # ----------------------------
    # PIPELINE MOVEMENT
    # ----------------------------
    # Eager load account for template rendering
    pipeline_activities = [a for a in activities_logged if 'Stage changed' in (a.subject or '')]
    pipeline_opp_ids = list(set(a.opportunity_id for a in pipeline_activities if a.opportunity_id))
    if pipeline_opp_ids:
        pipeline_changes = db.query(Opportunity).options(
            selectinload(Opportunity.account)
        ).filter(
            Opportunity.id.in_(pipeline_opp_ids)
        ).order_by(Opportunity.updated_at.desc()).all()
    else:
        pipeline_changes = []

    # ----------------------------
    # GENERATE SUMMARY SENTENCE (Personal language)
    # ----------------------------
    summary_parts = []
    if contacts_logged_count > 0:
        summary_parts.append(f"{contacts_logged_count} contact{'s' if contacts_logged_count != 1 else ''}")
    if activities_logged_count > 0:
        summary_parts.append(f"{activities_logged_count} activit{'ies' if activities_logged_count != 1 else 'y'}")
    if tasks_completed_count > 0:
        summary_parts.append(f"{tasks_completed_count} task{'s' if tasks_completed_count != 1 else ''}")
    if new_opportunities_count > 0:
        summary_parts.append(f"{new_opportunities_count} new opportunit{'ies' if new_opportunities_count != 1 else 'y'}")

    week_label = "This week" if is_current_week else f"Week of {start_date.strftime('%b %d')}"
    if summary_parts:
        summary_sentence = f"{week_label} you logged " + ", ".join(summary_parts) + "."
    else:
        summary_sentence = f"You haven't logged any activity for {week_label.lower()} yet."

    # Personal notes for this user
    section_notes = load_notes_for_week(db, week_start, user_id=user_id)

    return templates.TemplateResponse("summary/my_weekly.html", {
        "request": request,
        "start_date": start_date,
        "end_date": end_date,
        "week_start": week_start,
        "prev_week": prev_week,
        "next_week": next_week,
        "is_current_week": is_current_week,
        "summary_sentence": summary_sentence,
        # Counts
        "contacts_logged_count": contacts_logged_count,
        "new_contacts_count": new_contacts_count,
        "new_accounts_count": new_accounts_count,
        "opportunities_touched_count": opportunities_touched_count,
        "new_opportunities_count": new_opportunities_count,
        "tasks_completed_count": tasks_completed_count,
        "activities_logged_count": activities_logged_count,
        # Lists
        "outreach_contacts": outreach_contacts,
        "pipeline_changes": pipeline_changes,
        "tasks_completed": tasks_completed,
        "new_accounts": new_accounts,
        "new_contacts": new_contacts,
        "new_opportunities": new_opportunities,
        "activities_logged": activities_logged,
        # Notes
        "section_notes": section_notes,
    })
