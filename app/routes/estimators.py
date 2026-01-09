from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal

from app.database import get_db
from app.models import User, Opportunity

router = APIRouter(prefix="/estimators", tags=["estimators"])
templates = Jinja2Templates(directory="app/templates")


def calculate_estimator_workload(db: Session, estimator_id: int) -> dict:
    """
    Calculate workload metrics for an estimator.

    Returns:
        Dict with workload metrics:
            - active_opportunities: Count of open opportunities
            - total_pipeline_value: Sum of LV + HDD values
            - upcoming_bids: Count of bids in next 7 days
            - estimating_status_breakdown: Dict of status counts
            - opportunities: List of opportunity details
    """
    # Get all open opportunities for this estimator
    opportunities = db.query(Opportunity).filter(
        and_(
            Opportunity.assigned_estimator_id == estimator_id,
            Opportunity.stage.notin_(['Won', 'Lost'])
        )
    ).all()

    # Calculate metrics
    active_count = len(opportunities)
    total_value = sum(
        (float(opp.lv_value) if opp.lv_value else 0) +
        (float(opp.hdd_value) if opp.hdd_value else 0)
        for opp in opportunities
    )

    # Upcoming bids (next 7 days)
    seven_days_out = datetime.now().date() + timedelta(days=7)
    upcoming_bids = [
        opp for opp in opportunities
        if opp.bid_date and opp.bid_date <= seven_days_out
    ]

    # Estimating status breakdown
    status_breakdown = defaultdict(int)
    for opp in opportunities:
        status_breakdown[opp.estimating_status] += 1

    # Build opportunity details list
    opp_details = [{
        'id': opp.id,
        'name': opp.name,
        'account_name': opp.account.name if opp.account else 'Unknown',
        'stage': opp.stage,
        'value': (float(opp.lv_value) if opp.lv_value else 0) + (float(opp.hdd_value) if opp.hdd_value else 0),
        'bid_date': opp.bid_date,
        'estimating_status': opp.estimating_status,
        'days_until_bid': (opp.bid_date - datetime.now().date()).days if opp.bid_date else None
    } for opp in opportunities]

    # Sort by bid date (soonest first)
    opp_details.sort(key=lambda x: (x['bid_date'] is None, x['bid_date']))

    return {
        'active_opportunities': active_count,
        'total_pipeline_value': total_value,
        'upcoming_bids_count': len(upcoming_bids),
        'estimating_status_breakdown': dict(status_breakdown),
        'opportunities': opp_details
    }


@router.get("", response_class=HTMLResponse)
async def estimator_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Estimator workload dashboard showing capacity and assignments."""
    # Get all estimators (users with role=Estimator)
    estimators = db.query(User).filter(User.role == 'Estimator').all()

    # Calculate workload for each
    estimator_workloads = []
    for estimator in estimators:
        workload_data = calculate_estimator_workload(db, estimator.id)
        estimator_workloads.append({
            'estimator': estimator,
            **workload_data
        })

    # Determine capacity levels (green/yellow/red)
    for workload in estimator_workloads:
        active = workload['active_opportunities']
        upcoming = workload['upcoming_bids_count']

        # Capacity logic:
        # Green: < 5 active opportunities or < 3 upcoming bids
        # Yellow: 5-8 active or 3-5 upcoming
        # Red: > 8 active or > 5 upcoming
        if active <= 4 and upcoming <= 2:
            workload['capacity_level'] = 'green'
            workload['capacity_label'] = 'Available'
        elif active <= 7 and upcoming <= 4:
            workload['capacity_level'] = 'yellow'
            workload['capacity_label'] = 'Moderate'
        else:
            workload['capacity_level'] = 'red'
            workload['capacity_label'] = 'High Load'

    return templates.TemplateResponse("estimators/dashboard.html", {
        "request": request,
        "estimator_workloads": estimator_workloads,
    })


@router.get("/{estimator_id}/workload", response_class=JSONResponse)
async def get_estimator_workload_json(
    estimator_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get estimator workload as JSON (for AJAX calls)."""
    workload_data = calculate_estimator_workload(db, estimator_id)
    return JSONResponse(workload_data)


@router.get("/suggest-assignment", response_class=JSONResponse)
async def suggest_estimator_assignment(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Suggest which estimator to assign a new opportunity to.
    Returns estimator with lowest current workload.
    """
    # Get all estimators
    estimators = db.query(User).filter(User.role == 'Estimator').all()

    if not estimators:
        return JSONResponse({"suggested_estimator_id": None, "reason": "No estimators found"})

    # Calculate workload for each and find the one with lowest active opportunities
    min_workload = float('inf')
    suggested_estimator = None

    for estimator in estimators:
        workload = calculate_estimator_workload(db, estimator.id)
        active_count = workload['active_opportunities']

        if active_count < min_workload:
            min_workload = active_count
            suggested_estimator = estimator

    if suggested_estimator:
        return JSONResponse({
            "suggested_estimator_id": suggested_estimator.id,
            "suggested_estimator_name": suggested_estimator.full_name,
            "current_workload": min_workload,
            "reason": f"{suggested_estimator.full_name} has the lowest workload ({int(min_workload)} active opportunities)"
        })

    return JSONResponse({"suggested_estimator_id": None, "reason": "Unable to determine suggestion"})
