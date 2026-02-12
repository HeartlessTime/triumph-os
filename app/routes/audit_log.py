"""
Activity Audit Log Router

Provides a global, read-only view of all activities across the system.
Useful for compliance, tracking, and oversight purposes.
"""

from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Activity, Contact, Opportunity
from app.template_config import templates

router = APIRouter(tags=["audit"])

# Default page size
PAGE_SIZE = 50


@router.get("/audit-log", response_class=HTMLResponse)
async def audit_log(request: Request, page: int = 1, db: Session = Depends(get_db)):
    """
    Global activity audit log - read-only view of all activities.

    Query params:
        page: Page number (1-indexed), defaults to 1
        search: Text search on subject/description
        activity_type: Filter by activity type
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
    """
    # Ensure page is at least 1
    page = max(1, page)

    # Read filter params
    search = request.query_params.get("search", "").strip()
    activity_type = request.query_params.get("activity_type", "").strip()
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()

    # Build base query
    query = db.query(Activity)

    # Apply filters
    if search:
        term = f"%{search}%"
        query = query.filter(
            Activity.subject.ilike(term) | Activity.description.ilike(term)
        )

    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Activity.activity_date >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Activity.activity_date <= dt_to)
        except ValueError:
            pass

    # Get total count for pagination (after filters)
    total_count = query.count()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

    offset = (page - 1) * PAGE_SIZE

    # Query activities with eager loading to avoid N+1
    activities = (
        query
        .options(
            selectinload(Activity.created_by),
            selectinload(Activity.contact).selectinload(Contact.account),
            selectinload(Activity.opportunity).selectinload(Opportunity.account),
        )
        .order_by(Activity.activity_date.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
        .all()
    )

    # Build filter query string for pagination links
    filter_params = {}
    if search:
        filter_params["search"] = search
    if activity_type:
        filter_params["activity_type"] = activity_type
    if date_from:
        filter_params["date_from"] = date_from
    if date_to:
        filter_params["date_to"] = date_to

    return templates.TemplateResponse(
        "audit_log.html",
        {
            "request": request,
            "activities": activities,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "page_size": PAGE_SIZE,
            "activity_types": Activity.ACTIVITY_TYPES,
            "search": search,
            "activity_type": activity_type,
            "date_from": date_from,
            "date_to": date_to,
            "filter_params": filter_params,
        },
    )
