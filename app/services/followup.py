"""
Follow-up Engine Service

Rules for OPPORTUNITIES:
- Prospecting => last_contacted + 14 days
- Qualification => last_contacted + 7 days
- Needs Analysis => last_contacted + 7 days
- Proposal => last_contacted + 14 days
- Bid Sent => last_contacted + 14 days
- Negotiation => last_contacted + 7 days
- Won / Lost => no follow-up

If bid date has passed and status not Won/Lost => today + 2 business days

Auto-update next_followup whenever last_contacted or stage changes.
"""

from datetime import date, timedelta
from typing import Optional


# Stage to follow-up days mapping
STAGE_FOLLOWUP_DAYS = {
    'Prospecting': 14,
    'Qualification': 7,
    'Needs Analysis': 7,
    'Proposal': 14,
    'Bid Sent': 14,
    'Negotiation': 7,
}


def add_business_days(start_date: date, num_days: int) -> date:
    """
    Add business days (Monday-Friday) to a date.

    Args:
        start_date: The starting date
        num_days: Number of business days to add

    Returns:
        The resulting date after adding business days
    """
    current_date = start_date
    days_added = 0

    while days_added < num_days:
        current_date += timedelta(days=1)
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            days_added += 1

    return current_date


def calculate_next_followup(
    stage: str,
    last_contacted: Optional[date],
    bid_date: Optional[date],
    today: Optional[date] = None
) -> Optional[date]:
    """
    Calculate the next follow-up date based on opportunity stage and dates.

    Rules (in priority order):
    1. If Won/Lost => None (no follow-up)
    2. If bid date has passed => today + 2 business days (urgent)
    3. Stage-based: Prospecting/Proposal/Bid Sent = 14 days, others = 7 days

    Args:
        stage: The opportunity stage
        last_contacted: Date of last contact
        bid_date: Bid due date
        today: Current date (defaults to date.today())

    Returns:
        The calculated next follow-up date, or None
    """
    if today is None:
        today = date.today()

    # If opportunity is closed, no follow-up needed
    if stage in ('Won', 'Lost'):
        return None

    # If bid date has passed, urgent follow-up
    if bid_date and bid_date < today:
        return add_business_days(today, 2)

    # Stage-based follow-up
    followup_days = STAGE_FOLLOWUP_DAYS.get(stage)
    if followup_days:
        if last_contacted:
            return last_contacted + timedelta(days=followup_days)
        else:
            # If never contacted, follow up from today
            return today + timedelta(days=followup_days)

    # No automatic follow-up for unknown stages
    return None


def should_recalculate_followup(
    old_stage: Optional[str],
    new_stage: str,
    old_last_contacted: Optional[date],
    new_last_contacted: Optional[date],
    old_bid_date: Optional[date],
    new_bid_date: Optional[date]
) -> bool:
    """
    Determine if follow-up date should be recalculated.
    
    Returns True if:
    - Stage changed
    - Last contacted date changed
    - Bid date changed
    
    Args:
        old_stage: Previous stage value
        new_stage: New stage value
        old_last_contacted: Previous last_contacted date
        new_last_contacted: New last_contacted date
        old_bid_date: Previous bid_date
        new_bid_date: New bid_date
        
    Returns:
        True if follow-up should be recalculated
    """
    if old_stage != new_stage:
        return True
    if old_last_contacted != new_last_contacted:
        return True
    if old_bid_date != new_bid_date:
        return True
    return False


def get_followup_status(next_followup: Optional[date], today: Optional[date] = None) -> dict:
    """
    Get the status information for a follow-up date.
    
    Args:
        next_followup: The next follow-up date
        today: Current date (defaults to date.today())
        
    Returns:
        Dictionary with status info:
        - status: 'overdue', 'due_today', 'upcoming', 'none'
        - days_until: Number of days until follow-up (negative if overdue)
        - css_class: CSS class for styling
    """
    if today is None:
        today = date.today()
    
    if not next_followup:
        return {
            'status': 'none',
            'days_until': None,
            'css_class': ''
        }
    
    days_until = (next_followup - today).days
    
    if days_until < 0:
        return {
            'status': 'overdue',
            'days_until': days_until,
            'css_class': 'text-danger fw-bold'
        }
    elif days_until == 0:
        return {
            'status': 'due_today',
            'days_until': 0,
            'css_class': 'text-warning fw-bold'
        }
    elif days_until <= 3:
        return {
            'status': 'upcoming',
            'days_until': days_until,
            'css_class': 'text-info'
        }
    else:
        return {
            'status': 'upcoming',
            'days_until': days_until,
            'css_class': ''
        }
