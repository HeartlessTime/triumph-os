#!/usr/bin/env python3
"""
Contact Import Script for Triumph OS

Usage:
    python scripts/import_contacts.py path/to/contacts.csv

CSV columns expected:
    - account
    - notes
    - contact
    - title
    - email
    - mobile number
    - relevant projects
    - importance (ignored)

Behavior:
    - Matches accounts by name (case-insensitive)
    - Skips contacts if account doesn't exist
    - Creates new contacts if email doesn't exist
    - Updates existing contacts if email exists
    - Appends "relevant projects" to Account.notes (no duplicates)
    - Idempotent: safe to run multiple times
"""

import csv
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from app.database import SessionLocal
from app.models import Account, Contact, User


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def normalize(value: str) -> str:
    """Normalize string: strip whitespace and lowercase."""
    if not value:
        return ""
    return value.strip().lower()


def clean(value: str) -> str:
    """Clean string: strip whitespace, return None if empty."""
    if not value:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def split_name(full_name: str) -> tuple:
    """
    Split a full name into first_name and last_name.

    Examples:
        "John Smith" -> ("John", "Smith")
        "John" -> ("John", "")
        "John Paul Smith" -> ("John", "Paul Smith")
        "" -> ("Unknown", "")
    """
    if not full_name or not full_name.strip():
        return ("Unknown", "")

    parts = full_name.strip().split(None, 1)  # Split on first whitespace
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    return (first_name, last_name)


def append_to_notes(existing_notes: str, new_text: str, label: str = None) -> str:
    """
    Append new_text to existing_notes if not already present.
    Returns the combined notes.

    Args:
        existing_notes: Current notes content (may be None)
        new_text: Text to append
        label: Optional label for the separator (e.g., "Relevant Projects")
    """
    if not new_text or not new_text.strip():
        return existing_notes

    new_text = new_text.strip()

    if not existing_notes:
        return new_text

    # Check if already present (case-insensitive)
    if new_text.lower() in existing_notes.lower():
        return existing_notes

    # Append with separator
    if label:
        return f"{existing_notes}\n\n---\n{label}:\n{new_text}"
    else:
        return f"{existing_notes}\n\n---\n{new_text}"


# =============================================================================
# MAIN IMPORT LOGIC
# =============================================================================


def import_contacts(csv_path: str):
    """
    Import contacts from CSV file into database.

    Args:
        csv_path: Path to the CSV file
    """
    print("=" * 60)
    print("TRIUMPH OS - CONTACT IMPORT")
    print("=" * 60)
    print(f"CSV File: {csv_path}")
    print()

    # Validate file exists
    if not os.path.exists(csv_path):
        print(f"[ERROR] File not found: {csv_path}")
        sys.exit(1)

    # Counters
    rows_processed = 0
    created = 0
    updated = 0
    skipped_no_account = 0
    skipped_no_email = 0

    # Track accounts that have already had relevant_projects appended this run
    # Prevents redundant updates when multiple contacts share the same account
    accounts_updated_this_run = set()

    db = SessionLocal()

    try:
        # Get first active user for created_by_id
        default_user = db.query(User).filter(User.is_active == True).first()
        if not default_user:
            print("[ERROR] No active users found in database")
            sys.exit(1)

        print(f"Using default user: {default_user.full_name} (ID: {default_user.id})")
        print()

        # Read CSV
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                rows_processed += 1

                # Extract fields from CSV
                account_name = clean(row.get("account", ""))
                contact_name = clean(row.get("contact", ""))
                email = clean(row.get("email", ""))
                mobile = clean(row.get("mobile number", ""))
                title = clean(row.get("title", ""))
                notes = clean(row.get("notes", ""))
                relevant_projects = clean(row.get("relevant projects", ""))

                # Skip if no email (can't match/create without it)
                if not email:
                    print(f"  [SKIP_NO_EMAIL] Row {rows_processed}: No email provided for '{contact_name}'")
                    skipped_no_email += 1
                    continue

                # Normalize email for matching
                email_normalized = normalize(email)

                # Find account (case-insensitive)
                if not account_name:
                    print(f"  [SKIP_NO_ACCOUNT] Row {rows_processed}: No account name for '{email}'")
                    skipped_no_account += 1
                    continue

                account = db.query(Account).filter(
                    func.lower(Account.name) == normalize(account_name)
                ).first()

                if not account:
                    print(f"  [SKIP_NO_ACCOUNT] Row {rows_processed}: Account '{account_name}' not found for '{email}'")
                    skipped_no_account += 1
                    continue

                # Split contact name into first/last
                first_name, last_name = split_name(contact_name)

                # Check if contact exists (by email, case-insensitive)
                existing_contact = db.query(Contact).filter(
                    func.lower(Contact.email) == email_normalized
                ).first()

                if existing_contact:
                    # UPDATE existing contact
                    existing_contact.first_name = first_name
                    existing_contact.last_name = last_name
                    existing_contact.phone = mobile  # CSV "mobile number" -> phone field
                    existing_contact.title = title

                    # FIX: Append to existing notes instead of overwriting
                    # Preserves historical notes while adding new information
                    if notes:
                        existing_contact.notes = append_to_notes(
                            existing_contact.notes,
                            notes,
                            label="Import Notes"
                        )

                    # Note: We don't update account_id - contact stays with original account

                    print(f"  [UPDATED] Row {rows_processed}: {first_name} {last_name} <{email}> (Account: {account.name})")
                    updated += 1
                else:
                    # CREATE new contact
                    # Note: Contact model does not have created_by_id field
                    new_contact = Contact(
                        account_id=account.id,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        phone=mobile,  # CSV "mobile number" -> phone field
                        title=title,
                        notes=notes,
                    )
                    db.add(new_contact)

                    print(f"  [CREATED] Row {rows_processed}: {first_name} {last_name} <{email}> (Account: {account.name})")
                    created += 1

                # Append relevant projects to Account.notes (if provided)
                # FIX: Only update each account once per import run to prevent redundant updates
                if relevant_projects and account.id not in accounts_updated_this_run:
                    account.notes = append_to_notes(
                        account.notes,
                        relevant_projects,
                        label="Relevant Projects"
                    )
                    accounts_updated_this_run.add(account.id)

        # Commit all changes
        db.commit()

        # Print summary
        print()
        print("=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        print(f"Rows processed:       {rows_processed}")
        print(f"Contacts created:     {created}")
        print(f"Contacts updated:     {updated}")
        print(f"Skipped (no account): {skipped_no_account}")
        print(f"Skipped (no email):   {skipped_no_email}")
        print(f"Accounts updated:     {len(accounts_updated_this_run)}")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Import failed: {e}")
        raise

    finally:
        db.close()


# =============================================================================
# ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_contacts.py <csv_file>")
        print("Example: python scripts/import_contacts.py data/contacts.csv")
        sys.exit(1)

    csv_file = sys.argv[1]
    import_contacts(csv_file)
