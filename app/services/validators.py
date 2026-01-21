"""
Data Quality Validators

Centralized validation for Accounts, Contacts, and Opportunities.
All validation functions raise ValueError with human-readable messages.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models import Account, Contact, Opportunity, OpportunityAccount


class ValidationResult:
    """Container for validation results including warnings."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def raise_if_invalid(self):
        """Raise ValueError if there are blocking errors."""
        if self.errors:
            raise ValueError("; ".join(self.errors))


def _is_empty(value: Any) -> bool:
    """Check if value is None or empty string."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


# ============================================================
# ACCOUNT VALIDATION
# ============================================================


def validate_account(
    data: Dict[str, Any], db: Session, existing_id: Optional[int] = None
) -> ValidationResult:
    """
    Validate account data.

    Required fields: name only
    Block on duplicate account name (case-insensitive)
    City/state do NOT affect validation

    Args:
        data: Dict with keys: name, industry, city, state, etc.
        db: Database session for duplicate checks
        existing_id: ID of account being edited (for duplicate exclusion)

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult()

    # --- HARD REQUIRED FIELDS ---
    # Only account name is truly required
    if _is_empty(data.get("name")):
        result.add_error("Account name is required")

    # Industry, city, state are OPTIONAL - do not validate as required

    # --- DUPLICATE NAME CHECK (BLOCK) ---
    name = data.get("name", "").strip() if data.get("name") else ""

    if name:
        # Check for same name (case-insensitive) - this is a blocking error
        query = db.query(Account).filter(Account.name.ilike(name))
        if existing_id:
            query = query.filter(Account.id != existing_id)

        dupe_by_name = query.first()
        if dupe_by_name:
            result.add_error(f"Account already exists: {dupe_by_name.name}")

    # NOTE: City/state duplicates are intentionally NOT checked.
    # Multiple accounts can exist in the same city/state.

    return result


# ============================================================
# CONTACT VALIDATION
# ============================================================


def validate_contact(
    data: Dict[str, Any], db: Session, existing_id: Optional[int] = None
) -> ValidationResult:
    """
    Validate contact data.

    Required: first_name, last_name, account_id, and (email OR phone)
    Block: duplicate email globally
    Warn: same first+last+account

    Args:
        data: Dict with keys: first_name, last_name, account_id, email, phone, etc.
        db: Database session for duplicate checks
        existing_id: ID of contact being edited (for duplicate exclusion)

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult()

    # --- HARD REQUIRED FIELDS ---
    if _is_empty(data.get("first_name")):
        result.add_error("First name is required")

    # last_name is optional

    if _is_empty(data.get("account_id")):
        result.add_error("Account is required")

    # At least one of email OR phone required
    email = data.get("email", "").strip() if data.get("email") else ""
    phone = data.get("phone", "").strip() if data.get("phone") else ""
    mobile = data.get("mobile", "").strip() if data.get("mobile") else ""

    if not email and not phone and not mobile:
        result.add_error("At least one contact method is required (email or phone)")

    # --- DUPLICATE EMAIL (BLOCK) ---
    if email:
        query = db.query(Contact).filter(Contact.email.ilike(email))
        if existing_id:
            query = query.filter(Contact.id != existing_id)

        dupe_email = query.first()
        if dupe_email:
            result.add_error(
                f"Email '{email}' is already used by {dupe_email.full_name}"
            )

    # --- DUPLICATE NAME + ACCOUNT (WARN ONLY) ---
    first_name = data.get("first_name", "").strip() if data.get("first_name") else ""
    last_name = data.get("last_name", "").strip() if data.get("last_name") else ""
    account_id = data.get("account_id")

    if first_name and last_name and account_id:
        query = db.query(Contact).filter(
            Contact.first_name.ilike(first_name),
            Contact.last_name.ilike(last_name),
            Contact.account_id == account_id,
        )
        if existing_id:
            query = query.filter(Contact.id != existing_id)

        dupe_name = query.first()
        if dupe_name:
            result.add_warning(
                f"A contact named '{first_name} {last_name}' already exists for this account"
            )

    return result


# ============================================================
# OPPORTUNITY VALIDATION
# ============================================================


def validate_opportunity(
    data: Dict[str, Any],
    db: Session,
    existing_id: Optional[int] = None,
    old_stage: Optional[str] = None,
) -> ValidationResult:
    """
    Validate opportunity data.

    Required: at least one account, primary_account_id, stage, owner_id
    Optional: lv_value, hdd_value (validated if provided, must be >= 0)
    Validate: primary_account_id must be in account_ids
    Validate: primary_contact must belong to one of the selected accounts

    Args:
        data: Dict with opportunity fields
        db: Database session for duplicate checks
        existing_id: ID of opportunity being edited
        old_stage: Previous stage value (for stage change detection)

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult()

    # --- HARD REQUIRED FIELDS ---
    account_ids = data.get("account_ids", [])
    if not account_ids:
        result.add_error("At least one Account is required")

    primary_account_id = data.get("primary_account_id")
    if _is_empty(primary_account_id):
        result.add_error("Primary Account is required")
    elif account_ids and int(primary_account_id) not in [int(a) for a in account_ids]:
        result.add_error("Primary Account must be one of the selected Accounts")

    if _is_empty(data.get("stage")):
        result.add_error("Stage is required")

    if _is_empty(data.get("owner_id")):
        result.add_error("Owner is required")

    # --- VALIDATE PRIMARY CONTACT BELONGS TO SELECTED ACCOUNTS ---
    primary_contact_id = data.get("primary_contact_id")
    if primary_contact_id and account_ids:
        contact = db.query(Contact).filter(Contact.id == primary_contact_id).first()
        if contact and contact.account_id not in [int(a) for a in account_ids]:
            result.add_error("Primary Contact must belong to one of the selected Accounts")

    # --- VALUE VALIDATION (OPTIONAL): validate format if provided ---
    lv_value = data.get("lv_value")
    hdd_value = data.get("hdd_value")

    # Only validate if a value is provided - values are optional
    if lv_value:
        try:
            lv_num = Decimal(str(lv_value).replace(",", ""))
            if lv_num < 0:
                result.add_error("LV value cannot be negative")
        except:
            result.add_error("LV value must be a valid number")

    if hdd_value:
        try:
            hdd_num = Decimal(str(hdd_value).replace(",", ""))
            if hdd_num < 0:
                result.add_error("HDD value cannot be negative")
        except:
            result.add_error("HDD value must be a valid number")

    # --- DUPLICATE PREVENTION (WARN ONLY) ---
    name = data.get("name", "").strip() if data.get("name") else ""

    if name and account_ids:
        # Check for same name + any of the accounts within last 7 days
        seven_days_ago = date.today() - timedelta(days=7)

        # Check against opportunity_accounts table
        query = (
            db.query(Opportunity)
            .join(OpportunityAccount)
            .filter(
                Opportunity.name.ilike(name),
                OpportunityAccount.account_id.in_([int(a) for a in account_ids]),
                Opportunity.created_at >= seven_days_ago,
            )
        )
        if existing_id:
            query = query.filter(Opportunity.id != existing_id)

        dupe = query.first()
        if dupe:
            result.add_warning(
                f"An opportunity named '{name}' was created for one of these accounts within the last 7 days"
            )

    return result


def validate_opportunity_create(data: Dict[str, Any], db: Session) -> ValidationResult:
    """Validate opportunity on create (no existing ID, no old stage)."""
    return validate_opportunity(data, db, existing_id=None, old_stage=None)


def validate_opportunity_update(
    data: Dict[str, Any], db: Session, existing_id: int, old_stage: str
) -> ValidationResult:
    """Validate opportunity on update (with existing ID and old stage)."""
    return validate_opportunity(data, db, existing_id=existing_id, old_stage=old_stage)
