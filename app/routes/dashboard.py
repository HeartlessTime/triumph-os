from datetime import date, datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Contact, Activity
from app.services.dashboard_service import get_dashboard_data
from app.template_config import templates, get_app_tz

router = APIRouter(tags=["dashboard"])

# Feature flag: Set to True to use new dashboard_v2, False for original
USE_DASHBOARD_V2 = True


def get_week_start_monday(for_date: date = None) -> date:
    """Get the Monday of the week for a given date (or current week if None)."""
    target = for_date or datetime.now(get_app_tz()).date()
    days_since_monday = target.weekday()
    return target - timedelta(days=days_since_monday)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # Use app timezone for "today" to ensure consistent date comparisons
    today = datetime.now(get_app_tz()).date()
    data = get_dashboard_data(db, today)

    if not USE_DASHBOARD_V2:
        return templates.TemplateResponse(
            "dashboard/index.html", {"request": request, **data}
        )

    # Dashboard V2: Additional data for execution-focused view
    # Use same week boundaries as Weekly Summary for consistency
    week_start = get_week_start_monday(today)
    week_end = week_start + timedelta(days=6)
    start_datetime = datetime.combine(week_start, datetime.min.time())
    end_datetime = datetime.combine(week_end, datetime.max.time())

    # Contacts with follow-ups due today or overdue
    followup_contacts = (
        db.query(Contact)
        .options(selectinload(Contact.account))
        .filter(Contact.next_followup <= today)
        .order_by(Contact.next_followup)
        .all()
    )

    # Meetings pending: "meeting_requested" activities with a contact (all future)
    meetings_pending = (
        db.query(Activity)
        .options(selectinload(Activity.contact).selectinload(Contact.account))
        .filter(
            Activity.activity_type == "meeting_requested",
            Activity.contact_id.isnot(None),
        )
        .order_by(Activity.activity_date.desc())
        .all()
    )

    # Meetings completed: "meeting" activities during current week (same as Summary)
    meetings_completed = (
        db.query(Activity)
        .options(selectinload(Activity.contact).selectinload(Contact.account))
        .filter(
            Activity.activity_type == "meeting",
            Activity.activity_date >= start_datetime,
            Activity.activity_date <= end_datetime,
        )
        .order_by(Activity.activity_date.desc())
        .all()
    )

    return templates.TemplateResponse(
        "dashboard/dashboard_v2.html",
        {
            "request": request,
            **data,
            "followup_contacts": followup_contacts,
            "meetings_pending": meetings_pending,
            "meetings_completed": meetings_completed,
        },
    )
