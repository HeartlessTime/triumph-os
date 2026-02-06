"""
Daily Summary Route

Surfaces all actionable CRM items for today in a single scanning page.
"""

from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.daily_summary_service import get_daily_summary_data
from app.template_config import templates, get_app_tz

router = APIRouter(tags=["daily_summary"])


@router.get("/daily-summary", response_class=HTMLResponse)
async def daily_summary(request: Request, db: Session = Depends(get_db)):
    """Daily summary page — surfaces all actionable items for today."""
    today = datetime.now(get_app_tz()).date()
    data = get_daily_summary_data(db, today)

    return templates.TemplateResponse(
        "daily_summary/index.html",
        {"request": request, **data},
    )
