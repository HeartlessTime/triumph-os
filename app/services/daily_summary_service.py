"""
Daily Summary Service

Queries CRM data to surface actionable items for today:
- Contact follow-ups due
- Tasks due or overdue
- Account next actions due
"""

from datetime import date, timedelta
from sqlalchemy.orm import Session, selectinload

from app.models import Contact, Task, Account


def get_daily_summary_data(db: Session, today: date) -> dict:

    # --- Follow-Ups Due (Contacts) ---
    followup_contacts = (
        db.query(Contact)
        .options(selectinload(Contact.account))
        .filter(Contact.next_followup <= today)
        .order_by(Contact.next_followup)
        .all()
    )

    # --- Tasks Due Today or Overdue ---
    overdue_tasks = (
        db.query(Task)
        .options(selectinload(Task.opportunity))
        .filter(
            Task.status == "Open",
            Task.due_date.isnot(None),
            Task.due_date <= today,
        )
        .order_by(Task.due_date.nullslast())
        .all()
    )

    # --- Accounts with Next Actions Due (7 days) ---
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

    return {
        "today": today,
        "followup_contacts": followup_contacts,
        "overdue_tasks": overdue_tasks,
        "next_action_accounts": next_action_accounts,
    }
