#!/usr/bin/env python3
"""
Reset Demo Data Script
Usage: python -m app.scripts.reset_demo_data

SECURITY: This script is restricted to Garrett Garcia (ggarcia@triumph-cs.com) only.
WARNING: This script deletes ALL non-user data and replaces it with demo data.
         The users table is NEVER modified.
"""

import sys
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text

sys.path.insert(0, ".")

from app.database import SessionLocal, get_database_url
from app.models import (
    Account,
    Contact,
    Opportunity,
    Activity,
    Task,
    WeeklySummaryNote,
    User,
)

# ============================================================
# AUTHORIZATION - ONLY THIS USER CAN RUN THE SCRIPT
# ============================================================
AUTHORIZED_EMAIL = "ggarcia@triumph-cs.com"
AUTHORIZED_NAME = "Garrett Garcia"
CONFIRMATION_PHRASE = "RESET-DEMO-DATA"


def main():
    db_url = get_database_url()
    print(f"\n{'=' * 60}")
    print("DEMO DATA RESET SCRIPT")
    print(f"{'=' * 60}")
    print(f"Database: {db_url}\n")

    db = SessionLocal()

    try:
        # ============================================================
        # AUTHORIZATION GATE - HARD REQUIREMENT
        # ============================================================
        authorized_user = (
            db.query(User)
            .filter(User.email == AUTHORIZED_EMAIL, User.is_active == True)
            .first()
        )

        if not authorized_user:
            print("ERROR: Authorized user not found.")
            print(
                f"       This script requires: {AUTHORIZED_NAME} ({AUTHORIZED_EMAIL})"
            )
            print("       User must exist and be active in the database.")
            sys.exit(1)

        if authorized_user.full_name != AUTHORIZED_NAME:
            print("ERROR: User email matches but name does not.")
            print(f"       Expected: {AUTHORIZED_NAME}")
            print(f"       Found: {authorized_user.full_name}")
            sys.exit(1)

        print(f"AUTHORIZED USER: {authorized_user.full_name} ({authorized_user.email})")
        print("\nWARNING: This will DELETE all data except users:")
        print("  - All accounts")
        print("  - All contacts")
        print("  - All opportunities")
        print("  - All activities")
        print("  - All tasks")
        print("  - All weekly summary notes")
        print("\nThe USERS table will NOT be modified.\n")

        # ============================================================
        # CONFIRMATION - STRONGER PHRASE REQUIRED
        # ============================================================
        confirm = input(f"Type '{CONFIRMATION_PHRASE}' to proceed: ")
        if confirm.strip() != CONFIRMATION_PHRASE:
            print("\nAborted - confirmation phrase did not match.")
            sys.exit(0)

        print("\nProceeding with reset...\n")

        # Disable FK checks for SQLite
        db.execute(text("PRAGMA foreign_keys = OFF"))

        # Delete in FK-safe order (users table is NEVER touched)
        print("Deleting data...")
        print(f"  activities: {db.query(Activity).delete()}")
        print(f"  tasks: {db.query(Task).delete()}")
        print(f"  weekly_summary_notes: {db.query(WeeklySummaryNote).delete()}")
        print(f"  opportunities: {db.query(Opportunity).delete()}")
        print(f"  contacts: {db.query(Contact).delete()}")
        print(f"  accounts: {db.query(Account).delete()}")

        # === DEMO DATA ===
        today = date.today()
        now = datetime.utcnow()

        # Use the authorized user as the owner/creator for all demo data
        admin = authorized_user

        # Accounts
        accts = [
            Account(
                name="Austin ISD",
                industry="Education",
                phone="(512) 414-1700",
                city="Austin",
                state="TX",
                created_by_id=admin.id,
            ),
            Account(
                name="Dell Technologies",
                industry="Technology",
                phone="(800) 289-3355",
                city="Round Rock",
                state="TX",
                created_by_id=admin.id,
            ),
            Account(
                name="Seton Medical Center",
                industry="Healthcare",
                phone="(512) 324-1000",
                city="Austin",
                state="TX",
                created_by_id=admin.id,
            ),
        ]
        db.add_all(accts)
        db.flush()

        # Contacts
        contacts = [
            Contact(
                account_id=accts[0].id,
                first_name="Maria",
                last_name="Rodriguez",
                title="Facilities Director",
                email="maria@austinisd.org",
                is_primary=True,
            ),
            Contact(
                account_id=accts[0].id,
                first_name="James",
                last_name="Chen",
                title="Project Manager",
                email="james@austinisd.org",
            ),
            Contact(
                account_id=accts[1].id,
                first_name="Michael",
                last_name="Johnson",
                title="VP Facilities",
                email="michael@dell.com",
                is_primary=True,
            ),
            Contact(
                account_id=accts[1].id,
                first_name="Emily",
                last_name="Davis",
                title="Construction Mgr",
                email="emily@dell.com",
            ),
            Contact(
                account_id=accts[2].id,
                first_name="Robert",
                last_name="Martinez",
                title="COO",
                email="robert@seton.org",
                is_primary=True,
            ),
            Contact(
                account_id=accts[2].id,
                first_name="Jennifer",
                last_name="Taylor",
                title="Facilities Mgr",
                email="jennifer@seton.org",
            ),
        ]
        db.add_all(contacts)
        db.flush()

        # Opportunities
        opps = [
            Opportunity(
                account_id=accts[0].id,
                name="Eastside HS Network Upgrade",
                stage="Proposal",
                lv_value=Decimal("145000"),
                bid_date=today + timedelta(days=14),
                primary_contact_id=contacts[0].id,
                owner_id=admin.id,
            ),
            Opportunity(
                account_id=accts[0].id,
                name="Travis Elementary Security",
                stage="Prospecting",
                lv_value=Decimal("67000"),
                bid_date=today + timedelta(days=30),
                primary_contact_id=contacts[1].id,
                owner_id=admin.id,
            ),
            Opportunity(
                account_id=accts[1].id,
                name="Building 5 Data Center",
                stage="Negotiation",
                lv_value=Decimal("320000"),
                hdd_value=Decimal("45000"),
                bid_date=today + timedelta(days=7),
                primary_contact_id=contacts[2].id,
                owner_id=admin.id,
            ),
            Opportunity(
                account_id=accts[2].id,
                name="ED Renovation LV Systems",
                stage="Bid Sent",
                lv_value=Decimal("189000"),
                bid_date=today - timedelta(days=3),
                primary_contact_id=contacts[4].id,
                owner_id=admin.id,
                stalled_reason="Waiting on GC",
            ),
        ]
        db.add_all(opps)
        db.flush()

        # Activities
        activities = [
            Activity(
                opportunity_id=opps[0].id,
                contact_id=contacts[0].id,
                activity_type="meeting",
                subject="Scope review meeting",
                activity_date=now - timedelta(days=5),
                created_by_id=admin.id,
            ),
            Activity(
                opportunity_id=opps[0].id,
                contact_id=contacts[0].id,
                activity_type="email",
                subject="Sent preliminary scope",
                activity_date=now - timedelta(days=3),
                created_by_id=admin.id,
            ),
            Activity(
                opportunity_id=opps[1].id,
                contact_id=contacts[1].id,
                activity_type="call",
                subject="Intro call",
                activity_date=now - timedelta(days=7),
                created_by_id=admin.id,
            ),
            Activity(
                opportunity_id=opps[2].id,
                contact_id=contacts[2].id,
                activity_type="site_visit",
                subject="Site survey Building 5",
                activity_date=now - timedelta(days=4),
                created_by_id=admin.id,
            ),
            Activity(
                opportunity_id=opps[2].id,
                contact_id=contacts[3].id,
                activity_type="meeting",
                subject="Technical review",
                activity_date=now - timedelta(days=2),
                created_by_id=admin.id,
            ),
            Activity(
                opportunity_id=opps[3].id,
                contact_id=contacts[4].id,
                activity_type="email",
                subject="Submitted bid package",
                activity_date=now - timedelta(days=3),
                created_by_id=admin.id,
            ),
            Activity(
                opportunity_id=opps[3].id,
                contact_id=contacts[5].id,
                activity_type="call",
                subject="Follow-up on bid",
                activity_date=now - timedelta(days=1),
                created_by_id=admin.id,
            ),
        ]
        db.add_all(activities)

        # Tasks
        tasks = [
            Task(
                opportunity_id=opps[0].id,
                title="Complete takeoff for Eastside HS",
                due_date=today + timedelta(days=5),
                assigned_to_id=admin.id,
                created_by_id=admin.id,
            ),
            Task(
                opportunity_id=opps[0].id,
                title="Get vendor quotes for WAPs",
                due_date=today + timedelta(days=3),
                assigned_to_id=admin.id,
                created_by_id=admin.id,
            ),
            Task(
                opportunity_id=opps[2].id,
                title="Finalize Dell proposal",
                due_date=today + timedelta(days=2),
                assigned_to_id=admin.id,
                created_by_id=admin.id,
            ),
            Task(
                opportunity_id=opps[3].id,
                title="Follow up with Seton GC",
                due_date=today + timedelta(days=1),
                assigned_to_id=admin.id,
                created_by_id=admin.id,
            ),
            Task(
                title="Weekly pipeline review",
                due_date=today + timedelta(days=7),
                assigned_to_id=admin.id,
                created_by_id=admin.id,
            ),
        ]
        db.add_all(tasks)

        # Weekly Summary Notes
        week_start = today - timedelta(days=today.weekday())
        notes = [
            WeeklySummaryNote(
                week_start=week_start,
                section="outreach",
                user_id=admin.id,
                notes="Focus on Dell and Seton follow-ups.",
            ),
            WeeklySummaryNote(
                week_start=week_start,
                section="pipeline",
                user_id=admin.id,
                notes="$721K in active pipeline.",
            ),
        ]
        db.add_all(notes)

        # Re-enable FK checks
        db.execute(text("PRAGMA foreign_keys = ON"))

        db.commit()

        print("\nCreated:")
        print(f"  accounts: {len(accts)}")
        print(f"  contacts: {len(contacts)}")
        print(f"  opportunities: {len(opps)}")
        print(f"  activities: {len(activities)}")
        print(f"  tasks: {len(tasks)}")
        print(f"  weekly_summary_notes: {len(notes)}")
        print("\nDone! Demo data reset complete.\n")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
