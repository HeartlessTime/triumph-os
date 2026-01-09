from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.email_integration import get_email_integration
from app.background_jobs import scheduler

router = APIRouter(prefix="/email-sync", tags=["email_sync"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def email_sync_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Email sync dashboard and settings."""
    # Check if email integration is configured
    gmail_integration = get_email_integration(db, 'gmail')
    is_configured = gmail_integration is not None

    return templates.TemplateResponse("email_sync/dashboard.html", {
        "request": request,
        "is_configured": is_configured,
        "scheduler_running": scheduler.scheduler.running if scheduler else False,
    })


@router.post("/sync-now")
async def trigger_email_sync(
    request: Request,
    db: Session = Depends(get_db)
):
    """Manually trigger email sync."""
    # Get email integration
    email_integration = get_email_integration(db, 'gmail')

    if not email_integration:
        raise HTTPException(status_code=400, detail="Email integration not configured")

    # Run sync for last 7 days
    since_date = datetime.utcnow() - timedelta(days=7)
    stats = email_integration.sync_emails(since_date=since_date)

    # Return stats
    return templates.TemplateResponse("email_sync/results.html", {
        "request": request,
        "stats": stats,
    })
