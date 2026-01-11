"""
Activity Audit Log Router

Provides a global, read-only view of all activities across the system.
Useful for compliance, tracking, and oversight purposes.
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Activity, Contact, Opportunity

router = APIRouter(tags=["audit"])
templates = Jinja2Templates(directory="app/templates")

# Default page size
PAGE_SIZE = 50


@router.get("/audit-log", response_class=HTMLResponse)
async def audit_log(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Global activity audit log - read-only view of all activities.

    Query params:
        page: Page number (1-indexed), defaults to 1
    """
    # Ensure page is at least 1
    page = max(1, page)
    offset = (page - 1) * PAGE_SIZE

    # Get total count for pagination
    total_count = db.query(Activity).count()
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE  # Ceiling division

    # Query activities with eager loading to avoid N+1
    # Load: created_by (user), contact (with account), opportunity (with account)
    activities = db.query(Activity).options(
        selectinload(Activity.created_by),
        selectinload(Activity.contact).selectinload(Contact.account),
        selectinload(Activity.opportunity).selectinload(Opportunity.account)
    ).order_by(
        Activity.created_at.desc()
    ).offset(offset).limit(PAGE_SIZE).all()

    return templates.TemplateResponse("audit_log.html", {
        "request": request,
        "activities": activities,
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "page_size": PAGE_SIZE,
    })
