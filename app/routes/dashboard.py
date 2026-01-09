from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Opportunity, Account, Task, Activity, User
from app.services.followup import get_followup_status

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Main dashboard page."""
    today = date.today()

    # Get pipeline stats
    open_stages = ['Prospecting', 'Qualification', 'Needs Analysis', 'Proposal', 'Bid Sent', 'Negotiation']

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

    # Add value for each (days_until_bid is already a property)
    for opp in upcoming_bids:
        opp.value = (opp.lv_value or Decimal(0)) + (opp.hdd_value or Decimal(0))

    # My tasks
    my_tasks = db.query(Task)\
        .filter(Task.status == 'Open')\
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

    # Estimator capacity summary
    estimators = db.query(User).filter(User.role == 'Estimator').all()
    estimator_capacity = []
    for estimator in estimators:
        active_count = db.query(func.count(Opportunity.id)).filter(
            Opportunity.assigned_estimator_id == estimator.id,
            Opportunity.stage.in_(open_stages)
        ).scalar() or 0

        estimator_capacity.append({
            'name': estimator.full_name,
            'active_opportunities': active_count,
            'capacity_level': 'green' if active_count <= 4 else ('yellow' if active_count <= 7 else 'red')
        })

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
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
        "estimator_capacity": estimator_capacity,
    })
