"""
Daily Summary Service

Queries all CRM data to surface actionable items for today.
Mirrors query patterns from dashboard_service.py and dashboard.py.
"""

from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session, selectinload
import sqlalchemy as sa

from app.models import Opportunity, Contact, Task, Account, Activity, ActivityAttendee
from app.services.followup import get_followup_status


def get_daily_summary_data(db: Session, today: date) -> dict:
    open_stages = ["Prospecting", "Proposal", "Bid Sent", "Negotiation"]

    # --- Section 1: Overdue Follow-Ups (Opportunities) ---
    followup_opps = (
        db.query(Opportunity)
        .options(selectinload(Opportunity.account))
        .filter(
            Opportunity.stage.in_(open_stages),
            Opportunity.next_followup.isnot(None),
            Opportunity.next_followup <= today,
        )
        .order_by(Opportunity.next_followup)
        .all()
    )

    for opp in followup_opps:
        opp.followup_status = get_followup_status(opp.next_followup, today)

    # --- Section 2: Overdue Follow-Ups (Contacts) ---
    followup_contacts = (
        db.query(Contact)
        .options(selectinload(Contact.account))
        .filter(Contact.next_followup <= today)
        .order_by(Contact.next_followup)
        .all()
    )

    # --- Section 3: Tasks Due Today or Overdue ---
    overdue_tasks = (
        db.query(Task)
        .options(selectinload(Task.opportunity))
        .filter(
            Task.status == "Open",
            Task.due_date.isnot(None),
            Task.due_date <= today,
        )
        .order_by(Task.due_date.nullslast(), Task.priority.desc())
        .all()
    )

    # --- Section 4: Upcoming Bids (next 7 days) ---
    upcoming_bids = (
        db.query(Opportunity)
        .options(selectinload(Opportunity.account))
        .filter(
            Opportunity.stage.in_(open_stages),
            Opportunity.bid_date.isnot(None),
            Opportunity.bid_date >= today,
            Opportunity.bid_date <= today + timedelta(days=7),
        )
        .order_by(Opportunity.bid_date)
        .all()
    )

    # --- Section 5: Open Job Walks Needing Estimates ---
    jobs_awaiting_estimate = (
        db.query(Activity)
        .options(
            selectinload(Activity.contact).selectinload(Contact.account),
            selectinload(Activity.walk_segments),
        )
        .filter(
            Activity.activity_type == "job_walk",
            sa.or_(
                Activity.job_walk_status.in_(["open", "sent_to_estimator"]),
                Activity.job_walk_status.is_(None),
            ),
        )
        .order_by(
            Activity.estimate_due_by.asc().nullslast(),
            Activity.activity_date.desc(),
        )
        .all()
    )

    # --- Section 6: Accounts with Next Actions Due (7 days) ---
    next_action_accounts = (
        db.query(Account)
        .filter(
            Account.next_action.isnot(None),
            Account.next_action != "",
            Account.next_action_due_date.isnot(None),
            Account.next_action_due_date <= today + timedelta(days=7),
        )
        .order_by(Account.next_action_due_date)
        .all()
    )

    # --- Section 7: Hot Accounts (stalest first) ---
    hot_accounts = (
        db.query(Account)
        .options(selectinload(Account.contacts))
        .filter(Account.is_hot == True)
        .all()
    )
    hot_accounts.sort(key=lambda a: a.last_contacted or date.min)

    # --- Section 8: Meetings Pending ---
    meetings_pending = (
        db.query(Activity)
        .options(
            selectinload(Activity.contact).selectinload(Contact.account),
            selectinload(Activity.attendee_links).selectinload(
                ActivityAttendee.contact
            ),
        )
        .filter(
            Activity.activity_type == "meeting_requested",
            Activity.contact_id.isnot(None),
        )
        .order_by(Activity.activity_date.desc())
        .all()
    )

    # --- Section 9: Recent Activities (last 48 hours, context) ---
    cutoff = datetime.combine(today - timedelta(days=2), datetime.min.time())
    recent_activities = (
        db.query(Activity)
        .options(
            selectinload(Activity.opportunity),
            selectinload(Activity.contact),
        )
        .filter(Activity.activity_date >= cutoff)
        .order_by(Activity.activity_date.desc())
        .limit(15)
        .all()
    )

    return {
        "today": today,
        "followup_opps": followup_opps,
        "followup_contacts": followup_contacts,
        "overdue_tasks": overdue_tasks,
        "upcoming_bids": upcoming_bids,
        "jobs_awaiting_estimate": jobs_awaiting_estimate,
        "next_action_accounts": next_action_accounts,
        "hot_accounts": hot_accounts,
        "meetings_pending": meetings_pending,
        "recent_activities": recent_activities,
    }
