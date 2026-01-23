from datetime import date, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Contact, Activity
from app.services.dashboard_service import get_dashboard_data
from app.template_config import templates

router = APIRouter(tags=["dashboard"])

# Feature flag: Set to True to use new dashboard_v2, False for original
USE_DASHBOARD_V2 = True


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    data = get_dashboard_data(db, today)

    if not USE_DASHBOARD_V2:
        return templates.TemplateResponse(
            "dashboard/index.html", {"request": request, **data}
        )

    # Dashboard V2: Additional data for execution-focused view
    week_ago = today - timedelta(days=7)

    # Contacts with follow-ups due today or overdue
    followup_contacts = (
        db.query(Contact)
        .options(selectinload(Contact.account))
        .filter(Contact.next_followup <= today)
        .order_by(Contact.next_followup)
        .all()
    )

    # Meetings pending: "meeting_requested" activities with a contact
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

    # Meetings completed: "meeting" activities from last 7 days
    meetings_completed = (
        db.query(Activity)
        .options(selectinload(Activity.contact).selectinload(Contact.account))
        .filter(
            Activity.activity_type == "meeting",
            Activity.activity_date >= week_ago,
        )
        .order_by(Activity.activity_date.desc())
        .limit(10)
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
