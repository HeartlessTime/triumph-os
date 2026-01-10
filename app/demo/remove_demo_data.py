#!/usr/bin/env python3
"""
Demo Data Cleanup Script for Triumph OS CRM

Removes ALL demo data from the database.
Demo data is identified by the "Demo - " prefix in names/titles.

This script ONLY removes demo data and will NOT affect production data.

Usage:
    python -m app.demo.remove_demo_data
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models.account import Account
from app.models.contact import Contact
from app.models.opportunity import Opportunity
from app.models.task import Task
from app.models.activity import Activity


DEMO_PREFIX = "Demo - "


def remove_demo_data():
    """Remove all demo data from the database."""
    db = SessionLocal()

    try:
        print("Scanning for demo data...")

        # Count demo data before deletion
        demo_accounts = db.query(Account).filter(Account.name.like(f"{DEMO_PREFIX}%")).all()
        demo_tasks = db.query(Task).filter(Task.title.like(f"{DEMO_PREFIX}%")).all()

        # Get counts (Activities and Contacts will cascade with Accounts/Opportunities)
        account_count = len(demo_accounts)
        account_ids = [a.id for a in demo_accounts]

        if account_count == 0:
            print("No demo data found. Nothing to remove.")
            return False

        # Count related data
        contact_count = db.query(Contact).filter(Contact.account_id.in_(account_ids)).count() if account_ids else 0
        opp_count = db.query(Opportunity).filter(Opportunity.account_id.in_(account_ids)).count() if account_ids else 0

        # Get opportunity IDs for activity/task counts
        demo_opps = db.query(Opportunity).filter(Opportunity.account_id.in_(account_ids)).all() if account_ids else []
        opp_ids = [o.id for o in demo_opps]

        activity_count = db.query(Activity).filter(Activity.opportunity_id.in_(opp_ids)).count() if opp_ids else 0
        task_count = len(demo_tasks)

        print(f"\nFound demo data:")
        print(f"  - {account_count} Accounts")
        print(f"  - {contact_count} Contacts")
        print(f"  - {opp_count} Opportunities")
        print(f"  - {task_count} Tasks")
        print(f"  - {activity_count} Activities")

        # Confirm deletion
        print("\nThis will permanently delete all demo data.")
        response = input("Type 'DELETE' to confirm: ")

        if response != "DELETE":
            print("Aborted. No data was deleted.")
            return False

        print("\nDeleting demo data...")

        # Delete in order to respect foreign key constraints
        # Tasks first (some may be standalone)
        deleted_tasks = db.query(Task).filter(Task.title.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
        print(f"  Deleted {deleted_tasks} tasks")

        # Activities (will also cascade when opportunities are deleted)
        if opp_ids:
            deleted_activities = db.query(Activity).filter(Activity.opportunity_id.in_(opp_ids)).delete(synchronize_session=False)
            print(f"  Deleted {deleted_activities} activities")

        # Opportunities (cascade from accounts, but let's be explicit)
        if account_ids:
            deleted_opps = db.query(Opportunity).filter(Opportunity.account_id.in_(account_ids)).delete(synchronize_session=False)
            print(f"  Deleted {deleted_opps} opportunities")

        # Contacts (cascade from accounts, but let's be explicit)
        if account_ids:
            deleted_contacts = db.query(Contact).filter(Contact.account_id.in_(account_ids)).delete(synchronize_session=False)
            print(f"  Deleted {deleted_contacts} contacts")

        # Finally, accounts
        deleted_accounts = db.query(Account).filter(Account.name.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
        print(f"  Deleted {deleted_accounts} accounts")

        db.commit()

        print("\nDemo data removed successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Error removing demo data: {e}")
        raise
    finally:
        db.close()


def remove_demo_data_no_confirm():
    """Remove all demo data without confirmation prompt.

    Use this for automated cleanup (e.g., in tests or scripts).
    """
    db = SessionLocal()

    try:
        # Get account IDs first
        demo_accounts = db.query(Account).filter(Account.name.like(f"{DEMO_PREFIX}%")).all()
        account_ids = [a.id for a in demo_accounts]

        if not account_ids:
            print("No demo data found.")
            return False

        # Get opportunity IDs
        demo_opps = db.query(Opportunity).filter(Opportunity.account_id.in_(account_ids)).all()
        opp_ids = [o.id for o in demo_opps]

        # Delete in order
        db.query(Task).filter(Task.title.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)

        if opp_ids:
            db.query(Activity).filter(Activity.opportunity_id.in_(opp_ids)).delete(synchronize_session=False)

        if account_ids:
            db.query(Opportunity).filter(Opportunity.account_id.in_(account_ids)).delete(synchronize_session=False)
            db.query(Contact).filter(Contact.account_id.in_(account_ids)).delete(synchronize_session=False)

        db.query(Account).filter(Account.name.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)

        db.commit()
        print("Demo data removed successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Error removing demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Check for --force flag
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        remove_demo_data_no_confirm()
    else:
        remove_demo_data()
