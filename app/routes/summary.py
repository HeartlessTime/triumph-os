"""
Weekly Summary Router

Provides a read-only summary page showing work completed in the last 7 days.
Designed for boss-friendly reporting without authentication changes.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Account, Contact, Opportunity, Activity, Task, WeeklySummaryNote

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


def load_notes_for_week(db: Session, week_start: date) -> Dict[str, str]:
    """Load all notes for a given week, keyed by section."""
    notes = db.query(WeeklySummaryNote).filter(
        WeeklySummaryNote.week_start == week_start
    ).all()
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
    # 1) EXECUTIVE SUMMARY COUNTS
    # ----------------------------

    # Contacts where last_contacted was set/updated in the period
    # (This tracks log-contact actions)
    contacts_logged = db.query(Contact).filter(
        Contact.last_contacted >= start_date,
        Contact.last_contacted <= end_date
    ).all()
    contacts_logged_count = len(contacts_logged)

    # New contacts created
    new_contacts = db.query(Contact).filter(
        Contact.created_at >= start_datetime,
        Contact.created_at <= end_datetime
    ).order_by(Contact.created_at.desc()).all()
    new_contacts_count = len(new_contacts)

    # New accounts created
    new_accounts = db.query(Account).filter(
        Account.created_at >= start_datetime,
        Account.created_at <= end_datetime
    ).order_by(Account.created_at.desc()).all()
    new_accounts_count = len(new_accounts)

    # Opportunities touched (any update in the period)
    opportunities_touched = db.query(Opportunity).filter(
        Opportunity.updated_at >= start_datetime,
        Opportunity.updated_at <= end_datetime
    ).order_by(Opportunity.updated_at.desc()).all()
    opportunities_touched_count = len(opportunities_touched)

    # New opportunities created
    new_opportunities = db.query(Opportunity).filter(
        Opportunity.created_at >= start_datetime,
        Opportunity.created_at <= end_datetime
    ).order_by(Opportunity.created_at.desc()).all()
    new_opportunities_count = len(new_opportunities)

    # Tasks completed
    tasks_completed = db.query(Task).filter(
        Task.completed_at >= start_datetime,
        Task.completed_at <= end_datetime
    ).order_by(Task.completed_at.desc()).all()
    tasks_completed_count = len(tasks_completed)

    # Activities logged
    activities_logged = db.query(Activity).filter(
        Activity.activity_date >= start_datetime,
        Activity.activity_date <= end_datetime
    ).order_by(Activity.activity_date.desc()).all()
    activities_logged_count = len(activities_logged)

    # ----------------------------
    # 2) OUTREACH & FOLLOW-UPS
    # ----------------------------
    # Contacts where log-contact was used (last_contacted updated)
    outreach_contacts = db.query(Contact).filter(
        Contact.last_contacted >= start_date,
        Contact.last_contacted <= end_date
    ).order_by(Contact.last_contacted.desc()).all()

    # ----------------------------
    # 3) PIPELINE MOVEMENT
    # ----------------------------
    # Opportunities updated in the period (proxy for stage changes)
    # Since we don't have an audit log, show recently updated opportunities
    pipeline_changes = db.query(Opportunity).filter(
        Opportunity.updated_at >= start_datetime,
        Opportunity.updated_at <= end_datetime
    ).order_by(Opportunity.updated_at.desc()).all()

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
    # GENERATE SUMMARY SENTENCE
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
        summary_sentence = f"{week_label}: " + ", ".join(summary_parts) + "."
    else:
        summary_sentence = f"No activity recorded for {week_label.lower()}."

    # ----------------------------
    # LOAD NOTES FOR THIS WEEK
    # ----------------------------
    section_notes = load_notes_for_week(db, week_start)

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
    db: Session = Depends(get_db)
):
    """
    Save or update a note for a specific section and week.

    Form fields:
        week_start: The Monday of the week (YYYY-MM-DD)
        section: One of 'outreach', 'pipeline', 'tasks', 'new_records', 'other'
        notes: The note content (can be empty)
    """
    redirect_url = f"/summary/weekly?week_start={week_start}"

    # Validate section
    if section not in WeeklySummaryNote.SECTIONS:
        return RedirectResponse(url=redirect_url, status_code=303)

    # Find existing note or create new one
    existing = db.query(WeeklySummaryNote).filter(
        WeeklySummaryNote.week_start == week_start,
        WeeklySummaryNote.section == section
    ).first()

    if existing:
        existing.notes = notes
        existing.updated_at = datetime.utcnow()
    else:
        new_note = WeeklySummaryNote(
            week_start=week_start,
            section=section,
            notes=notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_note)

    db.commit()

    return RedirectResponse(url=redirect_url, status_code=303)
