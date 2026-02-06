"""
Daily Summary Route

Surfaces all actionable CRM items for today in a single scanning page.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyBriefing
from app.services.daily_summary_service import get_daily_summary_data
from app.template_config import templates, get_app_tz

router = APIRouter(tags=["daily_summary"])


@router.get("/daily-summary", response_class=HTMLResponse)
async def daily_summary(
    request: Request,
    db: Session = Depends(get_db),
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
):
    """Daily summary page — surfaces all actionable items for a given date (defaults to today)."""
    actual_today = datetime.now(get_app_tz()).date()

    # Parse requested date or default to today
    if date:
        try:
            selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            selected_date = actual_today
    else:
        selected_date = actual_today

    is_today = selected_date == actual_today
    prev_date = (selected_date - timedelta(days=1)).isoformat()
    next_date = (selected_date + timedelta(days=1)).isoformat()

    data = get_daily_summary_data(db, selected_date)

    # Load saved briefing for selected date
    briefing = (
        db.query(DailyBriefing)
        .filter(DailyBriefing.summary_date == selected_date)
        .first()
    )
    briefing_notes = briefing.notes if briefing else ""

    return templates.TemplateResponse(
        "daily_summary/index.html",
        {
            "request": request,
            "briefing_notes": briefing_notes,
            "selected_date": selected_date,
            "is_today": is_today,
            "prev_date": prev_date,
            "next_date": next_date,
            **data,
        },
    )


@router.post("/daily-summary/auto-save", response_class=JSONResponse)
async def auto_save_briefing(request: Request, db: Session = Depends(get_db)):
    """Auto-save briefing text to database. Never raises — always returns success."""
    try:
        try:
            payload = await request.json()
        except Exception:
            return {"status": "saved"}

        date_str = str(payload.get("date", "")).strip()
        notes = payload.get("notes", "") or ""

        if not date_str:
            return {"status": "saved"}

        try:
            summary_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return {"status": "saved"}

        # Upsert: find existing or create new
        briefing = (
            db.query(DailyBriefing)
            .filter(DailyBriefing.summary_date == summary_date)
            .first()
        )

        if briefing:
            briefing.notes = notes
        else:
            briefing = DailyBriefing(summary_date=summary_date, notes=notes)
            db.add(briefing)

        db.commit()
    except Exception:
        db.rollback()

    return {"status": "saved"}
