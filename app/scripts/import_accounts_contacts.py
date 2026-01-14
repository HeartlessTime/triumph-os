# app/scripts/import_accounts_contacts.py

import csv
import os
import re
from typing import Optional, Dict, Any

from app.database import SessionLocal
from app.models import Account, Contact


CSV_PATH_DEFAULT = "austin_targets.csv"  # rename your csv to this for simplicity


def norm(s: Optional[str]) -> str:
    """Normalize strings for matching."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip()).lower()


def pick(row: Dict[str, Any], *keys: str) -> str:
    """
    Try multiple possible column names.
    Returns the first non-empty value found.
    """
    for k in keys:
        if k in row and row[k] is not None and str(row[k]).strip() != "":
            return str(row[k]).strip()
    return ""


def main():
    csv_path = os.environ.get("IMPORT_CSV_PATH", CSV_PATH_DEFAULT)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"CSV not found at '{csv_path}'. Put it in repo root or set IMPORT_CSV_PATH."
        )

    db = SessionLocal()
    created_accounts = 0
    skipped_accounts = 0
    created_contacts = 0
    skipped_contacts = 0

    try:
        # Build a lookup of existing accounts by normalized name
        existing_accounts = db.query(Account).all()
        account_by_name = {norm(a.name): a for a in existing_accounts if a.name}

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            print("No rows found in CSV.")
            return

        print(f"Loaded {len(rows)} rows from {csv_path}")
        print("CSV columns:", list(rows[0].keys()))

        # We'll commit in batches
        BATCH_SIZE = 200
        pending = 0

        for i, row in enumerate(rows, start=1):
            # Account name candidates (adjust later if needed)
            account_name = pick(
                row,
                "Account",
                "Account Name",
                "Company",
                "Company Name",
                "Organization",
                "Name",
            )

            if not account_name:
                print(f"[SKIP] Row {i}: no account/company name")
                continue

            key = norm(account_name)

            # Create or find Account
            account = account_by_name.get(key)
            if account:
                skipped_accounts += 1
                print(f"[SKIP] Account exists: {account_name}")
            else:
                # Optional fields
                website = pick(row, "Website", "website", "URL", "url")
                notes = pick(row, "Notes", "notes", "Details", "details", "Description")

                account = Account(
                    name=account_name,
                    website=website or None if hasattr(Account, "website") else None,
                    notes=notes or None if hasattr(Account, "notes") else None,
                )

                # If Account model doesn't have website/notes, above may error.
                # Safer: set only attributes that exist.
                for attr, val in [("website", website), ("notes", notes)]:
                    if val and hasattr(account, attr):
                        setattr(account, attr, val)

                db.add(account)
                db.flush()  # get account.id
                account_by_name[key] = account
                created_accounts += 1
                print(f"[CREATE] Account: {account_name}")

                pending += 1

            # Contact fields (best effort)
            first_name = pick(row, "First Name", "first_name", "First")
            last_name = pick(row, "Last Name", "last_name", "Last")
            email = pick(row, "Email", "email")
            phone = pick(row, "Phone", "phone", "Office Phone", "Mobile")

            # Only create a contact if we have something meaningful
            has_contact = any([first_name, last_name, email, phone])
            if not has_contact:
                continue

            # If your Contact model is different, we’ll adjust after first run.
            # Dedup strategy: same email (if present) within same account.
            contact = None
            if email:
                contact = (
                    db.query(Contact)
                    .filter(Contact.account_id == account.id)
                    .filter(Contact.email.ilike(email))
                    .first()
                )

            if contact:
                skipped_contacts += 1
                print(f"[SKIP] Contact exists: {first_name} {last_name} ({email})")
            else:
                # Contact model likely has first_name/last_name/email/phone
                contact = Contact(
                    account_id=account.id,
                    first_name=first_name or None,
                    last_name=last_name or None,
                    email=email or None,
                    office_phone=phone or None if hasattr(Contact, "office_phone") else None,
                )
                # Set phone field safely
                if phone:
                    if hasattr(contact, "office_phone"):
                        contact.office_phone = phone
                    elif hasattr(contact, "phone"):
                        contact.phone = phone
                    elif hasattr(contact, "mobile"):
                        contact.mobile = phone

                db.add(contact)
                created_contacts += 1
                print(f"[CREATE] Contact: {first_name} {last_name} ({email or phone})")

                pending += 1

            # Batch commit
            if pending >= BATCH_SIZE:
                db.commit()
                pending = 0

        if pending:
            db.commit()

        print("\n=== IMPORT COMPLETE ===")
        print(f"Accounts created: {created_accounts}")
        print(f"Accounts skipped: {skipped_accounts}")
        print(f"Contacts created: {created_contacts}")
        print(f"Contacts skipped: {skipped_contacts}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
