"""
Today / This Week Route

Shows actionable items for today and the upcoming week:
- Opportunities needing follow-up (due today or overdue)
- Tasks due today or within next 7 days
- Opportunities with upcoming bid dates (next 7 days)
"""

from datetime import date, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_

from app.database import get_db
from app.models import Opportunity, Task, Contact

router = APIRouter(tags=["today"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/today", response_class=HTMLResponse)
async def today_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Today / This Week page showing actionable items."""
    today = date.today()
    week_from_now = today + timedelta(days=7)

    # Opportunities with follow-ups due today or overdue (only open opportunities)
    # Eager load account for template rendering (opp.account.name)
    followup_opps = db.query(Opportunity).options(
        selectinload(Opportunity.account)
    ).filter(
        Opportunity.next_followup <= today,
        Opportunity.stage.notin_(['Won', 'Lost'])
    ).order_by(Opportunity.next_followup).all()

    # Tasks due today or within next 7 days (only open tasks)
    # Eager load opportunity for template rendering (task.opportunity.name)
    upcoming_tasks = db.query(Task).options(
        selectinload(Task.opportunity)
    ).filter(
        Task.due_date <= week_from_now,
        Task.status == 'Open'
    ).order_by(Task.due_date, Task.priority.desc()).all()

    # Opportunities with bid dates in next 7 days (only open opportunities)
    # Eager load account for template rendering (opp.account.name)
    upcoming_bids = db.query(Opportunity).options(
        selectinload(Opportunity.account)
    ).filter(
        Opportunity.bid_date >= today,
        Opportunity.bid_date <= week_from_now,
        Opportunity.stage.notin_(['Won', 'Lost'])
    ).order_by(Opportunity.bid_date).all()

    return templates.TemplateResponse("today/index.html", {
        "request": request,
        "today": today,
        "followup_opps": followup_opps,
        "upcoming_tasks": upcoming_tasks,
        "upcoming_bids": upcoming_bids,
    })
