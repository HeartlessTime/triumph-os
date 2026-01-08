from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import JSON, Column, Integer, String, Text, DateTime
from datetime import datetime, timedelta
import json

from app.database import get_db, Base
from app.auth import get_current_user, DEMO_MODE
from app.models import Account, Opportunity, Activity, Contact
from app.ai_research import MeetingPrepResearcher

router = APIRouter(prefix="/meeting-prep", tags=["meeting_prep"])
templates = Jinja2Templates(directory="app/templates")


class MeetingBrief(Base):
    """Cache for meeting prep briefs."""
    __tablename__ = 'meeting_briefs'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, nullable=False, index=True)
    brief_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


@router.get("/account/{account_id}", response_class=HTMLResponse)
async def get_meeting_prep(
    request: Request,
    account_id: int,
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """Generate or retrieve meeting prep brief for an account."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/meeting-prep/account/{account_id}", status_code=303)

    # DEMO MODE: Show demo notice
    if DEMO_MODE or db is None:
        return templates.TemplateResponse("demo_mode_notice.html", {
            "request": request,
            "user": user,
            "feature": "AI Meeting Prep",
            "message": "AI-powered meeting prep is disabled in demo mode. This feature requires an Anthropic API key.",
            "back_url": f"/accounts/{account_id}",
        })

    # Get account
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check for cached brief (less than 24 hours old)
    cached_brief = None
    if not force_refresh:
        cached = db.query(MeetingBrief).filter(
            MeetingBrief.account_id == account_id,
            MeetingBrief.created_at > datetime.utcnow() - timedelta(hours=24)
        ).order_by(MeetingBrief.created_at.desc()).first()

        if cached:
            cached_brief = cached.brief_data

    # If no cache or force refresh, generate new brief
    if not cached_brief:
        try:
            # Gather internal context
            opportunities = db.query(Opportunity).filter(
                Opportunity.account_id == account_id
            ).order_by(Opportunity.created_at.desc()).limit(10).all()

            activities = db.query(Activity).join(Opportunity).filter(
                Opportunity.account_id == account_id
            ).order_by(Activity.activity_date.desc()).limit(10).all()

            contacts = db.query(Contact).filter(
                Contact.account_id == account_id
            ).all()

            # Build context dict
            internal_context = {
                'opportunities': [{
                    'name': opp.name,
                    'stage': opp.stage,
                    'value': float(opp.value) if opp.value else 0,
                    'bid_date': opp.bid_date.isoformat() if opp.bid_date else None
                } for opp in opportunities],
                'activities': [{
                    'date': act.activity_date.strftime('%Y-%m-%d'),
                    'type': act.type_display,
                    'subject': act.subject
                } for act in activities],
                'contacts': [{
                    'name': c.full_name,
                    'title': c.title,
                    'email': c.email
                } for c in contacts],
                'pipeline_value': float(account.total_pipeline_value) if account.total_pipeline_value else 0,
                'last_contact_date': activities[0].activity_date.strftime('%Y-%m-%d') if activities else None
            }

            # Call AI researcher
            researcher = MeetingPrepResearcher()
            brief_data = researcher.research_company(
                company_name=account.name,
                company_website=account.website,
                company_industry=account.industry,
                internal_context=internal_context
            )

            # Cache the brief
            cached_brief = brief_data
            new_brief = MeetingBrief(
                account_id=account_id,
                brief_data=brief_data
            )
            db.add(new_brief)
            db.commit()

        except Exception as e:
            # If research fails, show error
            return templates.TemplateResponse("error.html", {
                "request": request,
                "user": user,
                "error_title": "Research Failed",
                "error_message": f"Unable to generate meeting prep brief: {str(e)}",
                "back_url": f"/accounts/{account_id}",
            })

    # Render the brief
    return templates.TemplateResponse("meeting_prep/brief.html", {
        "request": request,
        "user": user,
        "account": account,
        "brief": cached_brief,
        "is_cached": not force_refresh and cached_brief,
    })


@router.post("/account/{account_id}/refresh")
async def refresh_meeting_prep(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db)
):
    """Force refresh meeting prep brief for an account."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Redirect to brief page with force_refresh flag
    return RedirectResponse(
        url=f"/meeting-prep/account/{account_id}?force_refresh=true",
        status_code=303
    )
