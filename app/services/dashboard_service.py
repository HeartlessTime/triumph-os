from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Opportunity, Task, Activity, User
from app.services.followup import get_followup_status


def get_dashboard_data(db: Session, today: date) -> dict:
    open_stages = ['Prospecting', 'Proposal', 'Bid Sent', 'Negotiation']

    pipeline_value = db.query(
        func.sum(func.coalesce(Opportunity.lv_value, 0) + func.coalesce(Opportunity.hdd_value, 0))
    ).filter(Opportunity.stage.in_(open_stages)).scalar() or 0

    stalled_count = db.query(func.count(Opportunity.id))\
        .filter(
            Opportunity.stage.in_(open_stages),
            Opportunity.stalled_reason.isnot(None),
            Opportunity.stalled_reason != ''
        )\
        .scalar() or 0

    open_opportunities = db.query(func.count(Opportunity.id))\
        .filter(Opportunity.stage.in_(open_stages))\
        .scalar() or 0

    first_of_month = today.replace(day=1)
    won_this_month = db.query(
        func.sum(func.coalesce(Opportunity.lv_value, 0) + func.coalesce(Opportunity.hdd_value, 0))
    ).filter(
        Opportunity.stage == 'Won',
        Opportunity.close_date >= first_of_month
    ).scalar() or 0

    followup_opps = db.query(Opportunity)\
        .filter(
            Opportunity.stage.in_(open_stages),
            Opportunity.next_followup.isnot(None),
            Opportunity.next_followup <= today
        )\
        .order_by(Opportunity.next_followup)\
        .limit(10)\
        .all()

    for opp in followup_opps:
        opp.followup_status = get_followup_status(opp.next_followup, today)

    upcoming_bids = db.query(Opportunity)\
        .filter(
            Opportunity.stage.in_(open_stages),
            Opportunity.bid_date.isnot(None),
            Opportunity.bid_date >= today,
            Opportunity.bid_date <= today + timedelta(days=14)
        )\
        .order_by(Opportunity.bid_date)\
        .limit(10)\
        .all()

    my_tasks = db.query(Task)\
        .filter(Task.status == 'Open')\
        .order_by(Task.due_date.nullslast(), Task.priority.desc())\
        .limit(10)\
        .all()

    recent_activities = db.query(Activity)\
        .order_by(Activity.activity_date.desc())\
        .limit(10)\
        .all()

    stage_counts = db.query(
        Opportunity.stage,
        func.count(Opportunity.id),
        func.sum(func.coalesce(Opportunity.lv_value, 0) + func.coalesce(Opportunity.hdd_value, 0))
    ).filter(
        Opportunity.stage.in_(open_stages)
    ).group_by(Opportunity.stage).all()

    stage_data = {row[0]: {'count': row[1], 'value': float(row[2] or 0)} for row in stage_counts}

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

    return {
        "pipeline_value": pipeline_value,
        "stalled_count": stalled_count,
        "open_opportunities": open_opportunities,
        "won_this_month": won_this_month,
        "followup_opps": followup_opps,
        "upcoming_bids": upcoming_bids,
        "my_tasks": my_tasks,
        "recent_activities": recent_activities,
        "stage_data": stage_data,
        "today": today,
        "estimator_capacity": estimator_capacity,
    }
