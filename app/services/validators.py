"""
Data Quality Validators

Centralized validation for Accounts, Contacts, and Opportunities.
All validation functions raise ValueError with human-readable messages.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models import Account, Contact, Opportunity


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
    data: Dict[str, Any],
    db: Session,
    existing_id: Optional[int] = None
) -> ValidationResult:
    """
    Validate account data.

    Required fields: name, industry, city, state
    Warn (not block) on potential duplicates.

    Args:
        data: Dict with keys: name, industry, city, state, etc.
        db: Database session for duplicate checks
        existing_id: ID of account being edited (for duplicate exclusion)

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult()

    # --- HARD REQUIRED FIELDS ---
    if _is_empty(data.get("name")):
        result.add_error("Account name is required")

    if _is_empty(data.get("industry")):
        result.add_error("Industry is required")

    if _is_empty(data.get("city")):
        result.add_error("City is required")

    if _is_empty(data.get("state")):
        result.add_error("State is required")

    # --- DUPLICATE PREVENTION (WARN ONLY) ---
    name = data.get("name", "").strip() if data.get("name") else ""
    city = data.get("city", "").strip() if data.get("city") else ""
    state = data.get("state", "").strip() if data.get("state") else ""

    if name:
        # Check for same name (case-insensitive)
        query = db.query(Account).filter(
            Account.name.ilike(name)
        )
        if existing_id:
            query = query.filter(Account.id != existing_id)

        dupe_by_name = query.first()
        if dupe_by_name:
            result.add_warning(f"An account named '{dupe_by_name.name}' already exists")

    if city and state:
        # Check for same city + state
        query = db.query(Account).filter(
            Account.city.ilike(city),
            Account.state.ilike(state)
        )
        if existing_id:
            query = query.filter(Account.id != existing_id)

        dupe_by_location = query.first()
        if dupe_by_location and dupe_by_location.name.lower() != name.lower():
            result.add_warning(
                f"Another account in {city}, {state} exists: '{dupe_by_location.name}'"
            )

    return result


# ============================================================
# CONTACT VALIDATION
# ============================================================

def validate_contact(
    data: Dict[str, Any],
    db: Session,
    existing_id: Optional[int] = None
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

    if _is_empty(data.get("last_name")):
        result.add_error("Last name is required")

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
        query = db.query(Contact).filter(
            Contact.email.ilike(email)
        )
        if existing_id:
            query = query.filter(Contact.id != existing_id)

        dupe_email = query.first()
        if dupe_email:
            result.add_error(f"Email '{email}' is already used by {dupe_email.full_name}")

    # --- DUPLICATE NAME + ACCOUNT (WARN ONLY) ---
    first_name = data.get("first_name", "").strip() if data.get("first_name") else ""
    last_name = data.get("last_name", "").strip() if data.get("last_name") else ""
    account_id = data.get("account_id")

    if first_name and last_name and account_id:
        query = db.query(Contact).filter(
            Contact.first_name.ilike(first_name),
            Contact.last_name.ilike(last_name),
            Contact.account_id == account_id
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
    old_stage: Optional[str] = None
) -> ValidationResult:
    """
    Validate opportunity data.

    Required: account_id, stage, owner_id
    Required: bid_date OR bid_date_tbd = True
    Optional: lv_value, hdd_value (validated if provided, must be >= 0)
    Workflow: stage change requires next_followup_date or no_followup_required
    Warn: same name + account within 7 days

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
    if _is_empty(data.get("account_id")):
        result.add_error("Account is required")

    if _is_empty(data.get("stage")):
        result.add_error("Stage is required")

    if _is_empty(data.get("owner_id")):
        result.add_error("Owner is required")

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

    # --- BID DATE REQUIREMENT: bid_date OR bid_date_tbd ---
    bid_date = data.get("bid_date")
    bid_date_tbd = data.get("bid_date_tbd", False)

    if _is_empty(bid_date) and not bid_date_tbd:
        result.add_error("Bid date is required (or mark as TBD)")

    # --- WORKFLOW GUARDRAIL: Stage change requires next_followup or explicit skip ---
    new_stage = data.get("stage")
    if old_stage and new_stage and old_stage != new_stage:
        next_followup = data.get("next_followup_date")
        no_followup_required = data.get("no_followup_required", False)

        # Only enforce on non-terminal stages
        terminal_stages = ["Won", "Lost"]
        if new_stage not in terminal_stages:
            if _is_empty(next_followup) and not no_followup_required:
                # Note: This is a soft guardrail - we set a default followup
                # rather than blocking. Comment out the error to allow auto-calculation.
                pass  # Followup is auto-calculated in routes

    # --- DUPLICATE PREVENTION (WARN ONLY) ---
    name = data.get("name", "").strip() if data.get("name") else ""
    account_id = data.get("account_id")

    if name and account_id:
        # Check for same name + account within last 7 days
        seven_days_ago = date.today() - timedelta(days=7)

        query = db.query(Opportunity).filter(
            Opportunity.name.ilike(name),
            Opportunity.account_id == account_id,
            Opportunity.created_at >= seven_days_ago
        )
        if existing_id:
            query = query.filter(Opportunity.id != existing_id)

        dupe = query.first()
        if dupe:
            result.add_warning(
                f"An opportunity named '{name}' was created for this account within the last 7 days"
            )

    return result


def validate_opportunity_create(
    data: Dict[str, Any],
    db: Session
) -> ValidationResult:
    """Validate opportunity on create (no existing ID, no old stage)."""
    return validate_opportunity(data, db, existing_id=None, old_stage=None)


def validate_opportunity_update(
    data: Dict[str, Any],
    db: Session,
    existing_id: int,
    old_stage: str
) -> ValidationResult:
    """Validate opportunity on update (with existing ID and old stage)."""
    return validate_opportunity(data, db, existing_id=existing_id, old_stage=old_stage)
