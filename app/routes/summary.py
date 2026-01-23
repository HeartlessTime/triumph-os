"""
Weekly Summary Router

Provides weekly summary pages:
- Team Weekly Summary: Shows ALL team activity (no user filter)
- My Weekly Summary: Shows only the current user's activity
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict

from fastapi import APIRouter, Request, Depends, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Account, Contact, Opportunity, Activity, Task, WeeklySummaryNote, UserSummarySuppression
from app.template_config import templates

router = APIRouter(prefix="/summary", tags=["summary"])


def get_week_start_monday(for_date: Optional[date] = None) -> date:
    """Get the Monday of the week for a given date (or current week if None)."""
    target = for_date or date.today()
    # weekday() returns 0 for Monday, 6 for Sunday
    days_since_monday = target.weekday()
    return target - timedelta(days=days_since_monday)


def get_week_boundaries_for_week(week_start: date):
    """Get start (Monday) and end (Sunday) dates for a given week."""
    return week_start, week_start + timedelta(days=6)


def load_notes_for_week(
    db: Session, week_start: date, user_id: Optional[int] = None
) -> Dict[str, str]:
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


def get_executive_summary(
    db: Session,
    start_datetime: datetime,
    end_datetime: datetime,
    user_id: Optional[int] = None,
    include_meetings: bool = True,
) -> Dict:
    """
    Get executive summary metrics for a date range.

    Args:
        db: Database session
        start_datetime: Start of period
        end_datetime: End of period
        user_id: None for team-wide totals, specific user ID for personal totals
        include_meetings: If False, exclude meeting activities (for team summaries)

    Returns:
        Dict with all summary data (counts and lists)
    """
    # ----------------------------
    # MASTER ACTIVITY QUERY
    # ----------------------------
    activity_query = (
        db.query(Activity)
        .options(
            selectinload(Activity.contact).selectinload(Contact.account),
            selectinload(Activity.opportunity),
        )
        .filter(
            Activity.activity_date >= start_datetime,
            Activity.activity_date <= end_datetime,
        )
    )

    if user_id is not None:
        activity_query = activity_query.filter(Activity.created_by_id == user_id)

    # Exclude meetings from team summaries (include_meetings=False)
    if not include_meetings:
        activity_query = activity_query.filter(Activity.activity_type != "meeting")

    activities_logged = activity_query.order_by(Activity.activity_date.desc()).all()
    activities_logged_count = len(activities_logged)

    # ----------------------------
    # CONTACTS LOGGED (from activities)
    # ----------------------------
    contacts_with_activity = [a for a in activities_logged if a.contact_id is not None]
    contacts_logged_ids = list(set(a.contact_id for a in contacts_with_activity))
    contacts_logged_count = len(contacts_logged_ids)

    # ----------------------------
    # OPPORTUNITIES TOUCHED (from activities)
    # ----------------------------
    opps_with_activity = [a for a in activities_logged if a.opportunity_id is not None]
    opportunities_touched_ids = list(set(a.opportunity_id for a in opps_with_activity))
    opportunities_touched_count = len(opportunities_touched_ids)

    if opportunities_touched_ids:
        opportunities_touched = (
            db.query(Opportunity)
            .options(selectinload(Opportunity.account))
            .filter(Opportunity.id.in_(opportunities_touched_ids))
            .order_by(Opportunity.updated_at.desc())
            .all()
        )
    else:
        opportunities_touched = []

    # ----------------------------
    # NEW ACCOUNTS
    # ----------------------------
    accounts_query = db.query(Account).filter(
        Account.created_at >= start_datetime, Account.created_at <= end_datetime
    )
    if user_id is not None:
        accounts_query = accounts_query.filter(Account.created_by_id == user_id)

    new_accounts = accounts_query.order_by(Account.created_at.desc()).all()
    new_accounts_count = len(new_accounts)

    # ----------------------------
    # NEW CONTACTS
    # ----------------------------
    contacts_query = (
        db.query(Contact)
        .options(selectinload(Contact.account))
        .filter(
            Contact.created_at >= start_datetime, Contact.created_at <= end_datetime
        )
    )

    # For personal summary, only show contacts from user's accounts or touched opportunities
    if user_id is not None:
        user_account_ids = [acc.id for acc in new_accounts]
        if opportunities_touched:
            # Get all account IDs from touched opportunities (via account_links)
            touched_account_ids = []
            for opp in opportunities_touched:
                touched_account_ids.extend(opp.account_ids)
            user_account_ids = list(set(user_account_ids + touched_account_ids))
        if user_account_ids:
            contacts_query = contacts_query.filter(
                Contact.account_id.in_(user_account_ids)
            )
        else:
            # No accounts = no contacts for this user
            contacts_query = contacts_query.filter(Contact.id == -1)  # Always false

    new_contacts = contacts_query.order_by(Contact.created_at.desc()).all()
    new_contacts_count = len(new_contacts)

    # ----------------------------
    # NEW OPPORTUNITIES
    # ----------------------------
    opps_query = db.query(Opportunity).filter(
        Opportunity.created_at >= start_datetime, Opportunity.created_at <= end_datetime
    )
    if user_id is not None:
        opps_query = opps_query.filter(Opportunity.owner_id == user_id)

    new_opportunities = opps_query.order_by(Opportunity.created_at.desc()).all()
    new_opportunities_count = len(new_opportunities)

    # ----------------------------
    # TASKS COMPLETED
    # ----------------------------
    tasks_query = (
        db.query(Task)
        .options(selectinload(Task.opportunity))
        .filter(
            Task.status == "Completed",
            Task.updated_at >= start_datetime,
            Task.updated_at <= end_datetime,
        )
    )
    if user_id is not None:
        # Personal: tasks completed BY this user
        tasks_query = tasks_query.filter(Task.completed_by_id == user_id)

    tasks_completed = tasks_query.order_by(Task.updated_at.desc()).all()
    tasks_completed_count = len(tasks_completed)

    # ----------------------------
    # OUTREACH ACTIVITIES (actual Activity records for editing)
    # ----------------------------
    # Return the actual Activity records so each row has a real ID for editing.
    # Previously returned deduplicated Contact objects which had no Activity ID.
    # Site visits are now shown in their own section
    outreach_types = ["call", "email", "other"]  # Excludes "meeting" and "site_visit" (shown separately)
    outreach_activities = [
        a for a in activities_logged
        if a.activity_type in outreach_types and a.contact_id is not None
    ]
    # Sort by activity_date descending (most recent first)
    outreach_activities.sort(key=lambda a: a.activity_date, reverse=True)

    # ----------------------------
    # SITE VISITS (separate section)
    # ----------------------------
    site_visits = [
        a for a in activities_logged
        if a.activity_type == "site_visit"
    ]
    site_visits.sort(key=lambda a: a.activity_date, reverse=True)

    # ----------------------------
    # PIPELINE CHANGES (from activities)
    # ----------------------------
    pipeline_activities = [
        a for a in activities_logged if "Stage changed" in (a.subject or "")
    ]
    pipeline_opp_ids = list(
        set(a.opportunity_id for a in pipeline_activities if a.opportunity_id)
    )

    if pipeline_opp_ids:
        pipeline_changes = (
            db.query(Opportunity)
            .options(selectinload(Opportunity.account))
            .filter(Opportunity.id.in_(pipeline_opp_ids))
            .order_by(Opportunity.updated_at.desc())
            .all()
        )
    else:
        pipeline_changes = []

    # ----------------------------
    # MEETINGS (from activities with type="meeting")
    # ----------------------------
    meetings = [a for a in activities_logged if a.activity_type == "meeting"]
    meetings_count = len(meetings)

    return {
        # Counts
        "contacts_logged_count": contacts_logged_count,
        "new_contacts_count": new_contacts_count,
        "new_accounts_count": new_accounts_count,
        "opportunities_touched_count": opportunities_touched_count,
        "new_opportunities_count": new_opportunities_count,
        "tasks_completed_count": tasks_completed_count,
        "activities_logged_count": activities_logged_count,
        "meetings_count": meetings_count,
        "outreach_count": len(outreach_activities),
        "site_visits_count": len(site_visits),
        # Lists
        "outreach_activities": outreach_activities,  # Activity records (editable)
        "site_visits": site_visits,  # Site visit activities (separate section)
        "pipeline_changes": pipeline_changes,
        "tasks_completed": tasks_completed,
        "new_accounts": new_accounts,
        "new_contacts": new_contacts,
        "new_opportunities": new_opportunities,
        "activities_logged": activities_logged,
        "meetings": meetings,
    }


@router.get("/weekly", response_class=HTMLResponse)
async def weekly_summary(
    request: Request, week_start: Optional[date] = None, db: Session = Depends(get_db)
):
    """
    Weekly summary page showing work completed in a specific week.

    Query params:
        week_start: Monday of the week to display (YYYY-MM-DD). Defaults to current week.
    """
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
    current_week = get_week_start_monday()
    is_current_week = week_start == current_week

    # Get team-wide executive summary (user_id=None, exclude meetings)
    # Meetings are personal activities and should only appear in My Weekly Summary
    summary = get_executive_summary(
        db, start_datetime, end_datetime, user_id=None, include_meetings=False
    )

    # Generate summary sentence (team-wide language)
    summary_parts = []
    if summary["contacts_logged_count"] > 0:
        summary_parts.append(
            f"{summary['contacts_logged_count']} contact{'s' if summary['contacts_logged_count'] != 1 else ''} logged"
        )
    if summary["activities_logged_count"] > 0:
        summary_parts.append(
            f"{summary['activities_logged_count']} activit{'ies' if summary['activities_logged_count'] != 1 else 'y'} recorded"
        )
    if summary["tasks_completed_count"] > 0:
        summary_parts.append(
            f"{summary['tasks_completed_count']} task{'s' if summary['tasks_completed_count'] != 1 else ''} completed"
        )
    if summary["new_opportunities_count"] > 0:
        summary_parts.append(
            f"{summary['new_opportunities_count']} new opportunit{'ies' if summary['new_opportunities_count'] != 1 else 'y'}"
        )

    week_label = (
        "This week" if is_current_week else f"Week of {start_date.strftime('%b %d')}"
    )
    if summary_parts:
        summary_sentence = (
            f"{week_label} the team logged " + ", ".join(summary_parts) + "."
        )
    else:
        summary_sentence = f"No team activity recorded for {week_label.lower()}."

    # Load team notes (user_id = NULL)
    section_notes = load_notes_for_week(db, week_start, user_id=None)

    return templates.TemplateResponse(
        "summary/weekly.html",
        {
            "request": request,
            "start_date": start_date,
            "end_date": end_date,
            "week_start": week_start,
            "prev_week": prev_week,
            "next_week": next_week,
            "is_current_week": is_current_week,
            "summary_sentence": summary_sentence,
            # Notes
            "section_notes": section_notes,
            # Spread all summary data
            **summary,
        },
    )


@router.post("/weekly/notes")
async def save_weekly_note(
    request: Request,
    week_start: date = Form(...),
    section: str = Form(...),
    notes: str = Form(""),
    note_type: str = Form("team"),
    db: Session = Depends(get_db),
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
        WeeklySummaryNote.week_start == week_start, WeeklySummaryNote.section == section
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
            updated_at=datetime.utcnow(),
        )
        db.add(new_note)

    db.commit()

    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/notes/auto-save")
async def auto_save_note(
    request: Request,
    db: Session = Depends(get_db),
):
    """Production-safe autosave. Never raises 422 or 500."""
    try:
        current_user = request.state.current_user
        if not current_user:
            return {"status": "saved"}

        # Try JSON first, fallback to form
        try:
            payload = await request.json()
        except Exception:
            try:
                form = await request.form()
                payload = dict(form)
            except Exception:
                payload = {}

        # Extract fields with safe defaults
        week_start_raw = payload.get("week_start", "")
        section = str(payload.get("section", "")).strip()
        notes_val = payload.get("notes", "") or ""
        note_type = str(payload.get("note_type", "team")).strip() or "team"

        # Validate required fields - return success but do nothing if missing
        if not week_start_raw or not section:
            return {"status": "saved"}

        # Parse week_start date
        try:
            week_start_date = datetime.strptime(str(week_start_raw).strip(), "%Y-%m-%d").date()
        except Exception:
            return {"status": "saved"}

        # Determine user_id based on note type
        if note_type == "personal":
            user_id = current_user.id
        else:
            user_id = None

        # Validate section - silently succeed if invalid
        if section not in WeeklySummaryNote.SECTIONS:
            return {"status": "saved"}

        # Find existing note or create new one
        query = db.query(WeeklySummaryNote).filter(
            WeeklySummaryNote.week_start == week_start_date,
            WeeklySummaryNote.section == section
        )
        if user_id is None:
            query = query.filter(WeeklySummaryNote.user_id.is_(None))
        else:
            query = query.filter(WeeklySummaryNote.user_id == user_id)

        existing = query.first()

        if existing:
            existing.notes = notes_val
            existing.updated_at = datetime.utcnow()
        else:
            new_note = WeeklySummaryNote(
                week_start=week_start_date,
                section=section,
                user_id=user_id,
                notes=notes_val,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_note)

        try:
            db.commit()
        except Exception:
            db.rollback()

        return {"status": "saved"}
    except Exception:
        return {"status": "saved"}


@router.get("/my-weekly", response_class=HTMLResponse)
async def my_weekly_summary(
    request: Request, week_start: Optional[date] = None, db: Session = Depends(get_db)
):
    """
    Personal weekly summary showing work the current user completed.

    Filters all data to the current user:
    - Tasks completed BY this user (completed_by_id)
    - Activities logged BY this user (created_by_id)
    - Opportunities owned BY this user (owner_id)
    - Accounts created BY this user (created_by_id)
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
    is_current_week = week_start == current_week_monday

    # Get personal executive summary (user_id=current user)
    summary = get_executive_summary(db, start_datetime, end_datetime, user_id=user_id)

    # Generate summary sentence (personal language)
    summary_parts = []
    if summary["contacts_logged_count"] > 0:
        summary_parts.append(
            f"{summary['contacts_logged_count']} contact{'s' if summary['contacts_logged_count'] != 1 else ''}"
        )
    if summary["activities_logged_count"] > 0:
        summary_parts.append(
            f"{summary['activities_logged_count']} activit{'ies' if summary['activities_logged_count'] != 1 else 'y'}"
        )
    if summary["tasks_completed_count"] > 0:
        summary_parts.append(
            f"{summary['tasks_completed_count']} task{'s' if summary['tasks_completed_count'] != 1 else ''}"
        )
    if summary["new_opportunities_count"] > 0:
        summary_parts.append(
            f"{summary['new_opportunities_count']} new opportunit{'ies' if summary['new_opportunities_count'] != 1 else 'y'}"
        )

    week_label = (
        "This week" if is_current_week else f"Week of {start_date.strftime('%b %d')}"
    )
    if summary_parts:
        summary_sentence = f"{week_label} you logged " + ", ".join(summary_parts) + "."
    else:
        summary_sentence = (
            f"You haven't logged any activity for {week_label.lower()} yet."
        )

    # Personal notes for this user
    section_notes = load_notes_for_week(db, week_start, user_id=user_id)

    # Get suppressed opportunity IDs for this user
    suppressed_ids = get_suppressed_opportunity_ids(db, user_id)

    # Filter pipeline_changes to exclude suppressed opportunities
    # (unless they have new activity after suppression - handled in get_suppressed_opportunity_ids)
    filtered_pipeline = [
        opp for opp in summary["pipeline_changes"]
        if opp.id not in suppressed_ids
    ]

    return templates.TemplateResponse(
        "summary/my_weekly.html",
        {
            "request": request,
            "start_date": start_date,
            "end_date": end_date,
            "week_start": week_start,
            "prev_week": prev_week,
            "next_week": next_week,
            "is_current_week": is_current_week,
            "summary_sentence": summary_sentence,
            # Notes
            "section_notes": section_notes,
            # Spread all summary data (with filtered pipeline)
            **{**summary, "pipeline_changes": filtered_pipeline},
        },
    )


def get_suppressed_opportunity_ids(db: Session, user_id: int) -> set:
    """
    Get set of opportunity IDs currently suppressed for a user.

    An opportunity is suppressed UNLESS it has new pipeline activity (Activity with
    "Stage changed" in subject) after the suppression timestamp.
    """
    suppressions = (
        db.query(UserSummarySuppression)
        .filter(UserSummarySuppression.user_id == user_id)
        .all()
    )

    suppressed_ids = set()
    for supp in suppressions:
        # Check if there's any new pipeline activity after suppression
        new_activity = (
            db.query(Activity)
            .filter(
                Activity.opportunity_id == supp.opportunity_id,
                Activity.subject.ilike("%Stage changed%"),
                Activity.activity_date > supp.suppressed_at,
            )
            .first()
        )
        if new_activity:
            # New pipeline activity detected - remove the suppression
            db.delete(supp)
            db.commit()
        else:
            suppressed_ids.add(supp.opportunity_id)

    return suppressed_ids


@router.post("/suppress-opportunity/{opportunity_id}")
async def suppress_opportunity(
    request: Request,
    opportunity_id: int,
    week_start: date = Form(None),
    db: Session = Depends(get_db),
):
    """
    Suppress an opportunity from the current user's personal summary.

    The opportunity will be hidden until new pipeline activity occurs.
    """
    current_user = request.state.current_user

    # Check if already suppressed
    existing = (
        db.query(UserSummarySuppression)
        .filter(
            UserSummarySuppression.user_id == current_user.id,
            UserSummarySuppression.opportunity_id == opportunity_id,
        )
        .first()
    )

    if not existing:
        suppression = UserSummarySuppression(
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            suppressed_at=datetime.utcnow(),
        )
        db.add(suppression)
        db.commit()

    # Redirect back to my weekly summary
    redirect_url = "/summary/my-weekly"
    if week_start:
        redirect_url += f"?week_start={week_start}"
    return RedirectResponse(url=redirect_url, status_code=303)
