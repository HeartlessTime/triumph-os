from datetime import date, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user, DEMO_MODE
from app.models import Opportunity, Account, Task, Activity
from app.services.followup import get_followup_status

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Main dashboard page."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    today = date.today()

    # Get pipeline stats
    open_stages = ['Prospecting', 'Qualification', 'Needs Analysis', 'Proposal', 'Bid Sent', 'Negotiation']

    # DEMO MODE: Return mock data
    if DEMO_MODE or db is None:
        pipeline_value = 0
        weighted_pipeline = 0
        open_opportunities = 0
        won_this_month = 0
        followup_opps = []
        upcoming_bids = []
        my_tasks = []
        recent_activities = []
        stage_data = {}
    else:
        # Pipeline value: sum of LV + HDD estimates
        pipeline_value = db.query(
            func.sum(func.coalesce(Opportunity.lv_value, 0) + func.coalesce(Opportunity.hdd_value, 0))
        ).filter(Opportunity.stage.in_(open_stages)).scalar() or 0

        # Weighted pipeline disabled (probability not used)
        weighted_pipeline = 0

        open_opportunities = db.query(func.count(Opportunity.id))\
            .filter(Opportunity.stage.in_(open_stages))\
            .scalar() or 0

        # Won this month
        first_of_month = today.replace(day=1)
        won_this_month = db.query(func.sum(func.coalesce(Opportunity.lv_value, 0) + func.coalesce(Opportunity.hdd_value, 0)))\
            .filter(
                Opportunity.stage == 'Won',
                Opportunity.close_date >= first_of_month
            ).scalar() or 0

        # Opportunities needing follow-up
        followup_opps = db.query(Opportunity)\
            .filter(
                Opportunity.stage.in_(open_stages),
                Opportunity.next_followup <= today
            )\
            .order_by(Opportunity.next_followup)\
            .limit(10)\
            .all()

        # Add followup status to each opportunity
        for opp in followup_opps:
            opp.followup_status = get_followup_status(opp.next_followup, today)

        # Upcoming bids
        upcoming_bids = db.query(Opportunity)\
            .filter(
                Opportunity.stage.in_(open_stages),
                Opportunity.bid_date >= today,
                Opportunity.bid_date <= today + timedelta(days=14)
            )\
            .order_by(Opportunity.bid_date)\
            .limit(10)\
            .all()

        # My tasks
        if user.is_admin:
            my_tasks = db.query(Task)\
                .filter(Task.status == 'Open')\
                .order_by(Task.due_date.nullslast(), Task.priority.desc())\
                .limit(10)\
                .all()
        else:
            my_tasks = db.query(Task)\
                .filter(
                    Task.status == 'Open',
                    Task.assigned_to_id == user.id
                )\
                .order_by(Task.due_date.nullslast(), Task.priority.desc())\
                .limit(10)\
                .all()

        # Recent activities
        recent_activities = db.query(Activity)\
            .order_by(Activity.activity_date.desc())\
            .limit(10)\
            .all()

        # Stage distribution for pipeline chart
        stage_counts = db.query(
            Opportunity.stage,
            func.count(Opportunity.id),
            func.sum(func.coalesce(Opportunity.lv_value, 0) + func.coalesce(Opportunity.hdd_value, 0))
        ).filter(
            Opportunity.stage.in_(open_stages)
        ).group_by(Opportunity.stage).all()

        stage_data = {row[0]: {'count': row[1], 'value': float(row[2] or 0)} for row in stage_counts}

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "pipeline_value": pipeline_value,
        "weighted_pipeline": weighted_pipeline,
        "open_opportunities": open_opportunities,
        "won_this_month": won_this_month,
        "followup_opps": followup_opps,
        "upcoming_bids": upcoming_bids,
        "my_tasks": my_tasks,
        "recent_activities": recent_activities,
        "stage_data": stage_data,
        "today": today,
    })
