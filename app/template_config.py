"""Centralized Jinja2 template configuration with timezone support."""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi.templating import Jinja2Templates

# App timezone setting - defaults to Central Time
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Chicago")


def get_app_tz() -> ZoneInfo:
    """Get the application timezone."""
    return ZoneInfo(APP_TIMEZONE)


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime. Use this instead of datetime.now()."""
    return datetime.now(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """Convert a datetime to the app's local timezone for display.

    Handles both naive and aware datetimes:
    - Naive datetimes are assumed to be UTC
    - Aware datetimes are converted to local timezone
    """
    if dt is None:
        return None

    app_tz = get_app_tz()

    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to local timezone
    return dt.astimezone(app_tz)


def localtime(dt: datetime, fmt: str = None) -> str:
    """Jinja filter to convert UTC datetime to local time string.

    Usage in templates:
        {{ activity.activity_date | localtime }}
        {{ activity.activity_date | localtime('%b %d, %H:%M') }}
    """
    if dt is None:
        return ""

    local_dt = to_local(dt)

    if fmt:
        return local_dt.strftime(fmt)

    # Default format: "Jan 15, 14:30"
    return local_dt.strftime("%b %d, %H:%M")


def localdate(dt: datetime, fmt: str = None) -> str:
    """Jinja filter to convert UTC datetime to local date string.

    Usage in templates:
        {{ opportunity.created_at | localdate }}
        {{ opportunity.created_at | localdate('%B %d, %Y') }}
    """
    if dt is None:
        return ""

    local_dt = to_local(dt)

    if fmt:
        return local_dt.strftime(fmt)

    # Default format: "Jan 15, 2025"
    return local_dt.strftime("%b %d, %Y")


def create_templates() -> Jinja2Templates:
    """Create a Jinja2Templates instance with custom filters."""
    templates = Jinja2Templates(directory="app/templates")

    # Add timezone filters
    templates.env.filters["localtime"] = localtime
    templates.env.filters["localdate"] = localdate

    return templates


# Singleton template instance - import this in route files
templates = create_templates()
