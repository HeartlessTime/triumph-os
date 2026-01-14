import logging
from datetime import datetime, date
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Opportunity, Activity, Contact
from app.services.followup import calculate_next_followup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activities", tags=["activities"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/opportunity/{opp_id}/add")
async def add_activity(
    request: Request,
    opp_id: int,
    activity_type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    activity_date: str = Form(None),
    contact_id: int = Form(None),
    update_last_contacted: bool = Form(True),
    db: Session = Depends(get_db),
):
    """Add an activity to an opportunity."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Parse activity date
    if activity_date:
        activity_dt = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
    else:
        activity_dt = datetime.now()

    current_user = request.state.current_user
    activity = Activity(
        opportunity_id=opp_id,
        activity_type=activity_type,
        subject=subject,
        description=description or None,
        activity_date=activity_dt,
        contact_id=contact_id if contact_id else None,
        created_by_id=current_user.id,
    )

    db.add(activity)

    # Update last_contacted if requested and activity is today or in the past
    if update_last_contacted and activity_dt.date() <= date.today():
        opportunity.last_contacted = activity_dt.date()
        # Recalculate followup
        opportunity.next_followup = calculate_next_followup(
            stage=opportunity.stage,
            last_contacted=opportunity.last_contacted,
            bid_date=opportunity.bid_date,
        )

    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.get("/{activity_id}/edit", response_class=HTMLResponse)
async def edit_activity_form(
    request: Request, activity_id: int, db: Session = Depends(get_db)
):
    """Display edit activity form.

    Activities can belong to:
    - An Opportunity (with optional Contact)
    - A Contact only (no Opportunity)
    - Neither (orphaned activity - logged but navigable)

    GUARDRAILS:
    - Never assumes activity.opportunity exists
    - Safely determines context owner for contact dropdown
    - Prevents full-table queries by requiring account_id filter
    - Logs warning for orphaned activities
    """
    # 1. Immediate 404 if activity doesn't exist
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 2. Determine context owner account_id (NEVER assume opportunity exists)
    context_account_id = None
    contacts = []

    if activity.opportunity is not None:
        # Activity is linked to an opportunity - use opportunity's account
        context_account_id = activity.opportunity.account_id
    elif activity.contact is not None:
        # Activity is linked to a contact only - use contact's account
        context_account_id = activity.contact.account_id
    else:
        # Orphaned activity - has neither opportunity nor contact
        logger.warning(
            f"Activity {activity_id} has no opportunity or contact. "
            f"Type: {activity.activity_type}, Subject: {activity.subject}"
        )

    # 3. Only query contacts if we have a valid account_id (prevents full-table scan)
    if context_account_id is not None:
        contacts = (
            db.query(Contact)
            .filter(Contact.account_id == context_account_id)
            .order_by(Contact.last_name)
            .all()
        )

    return templates.TemplateResponse(
        "activities/edit.html",
        {
            "request": request,
            "activity": activity,
            "contacts": contacts,
            "activity_types": Activity.ACTIVITY_TYPES,
        },
    )


@router.post("/{activity_id}/edit")
async def update_activity(
    request: Request,
    activity_id: int,
    activity_type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    activity_date: str = Form(...),
    contact_id: int = Form(None),
    db: Session = Depends(get_db),
):
    """Update an activity.

    REDIRECT RULE ORDER:
    1. If ?from= query param exists → use that URL (back navigation)
    2. Else if activity.opportunity exists → /opportunities/{id}
    3. Else if activity.contact exists → /contacts/{id}
    4. Else → /summary/my-weekly
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check for explicit return URL from query params (back navigation)
    from_url = request.query_params.get("from")
    if from_url:
        redirect_url = from_url
    elif activity.opportunity_id:
        redirect_url = f"/opportunities/{activity.opportunity_id}"
    elif activity.contact_id:
        redirect_url = f"/contacts/{activity.contact_id}"
    else:
        redirect_url = "/summary/my-weekly"

    # Apply updates
    activity.activity_type = activity_type
    activity.subject = subject
    activity.description = description or None
    activity.activity_date = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
    activity.contact_id = contact_id if contact_id else None

    db.commit()

    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/{activity_id}/delete")
async def delete_activity(
    request: Request, activity_id: int, db: Session = Depends(get_db)
):
    """Delete an activity.

    REDIRECT RULE ORDER:
    1. If ?from= query param exists → use that URL (back navigation)
    2. Else if activity.opportunity_id exists → /opportunities/{id}
    3. Else if activity.contact_id exists → /contacts/{id}
    4. Else → /summary/my-weekly
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check for explicit return URL from query params (back navigation)
    from_url = request.query_params.get("from")
    if from_url:
        redirect_url = from_url
    elif activity.opportunity_id:
        redirect_url = f"/opportunities/{activity.opportunity_id}"
    elif activity.contact_id:
        redirect_url = f"/contacts/{activity.contact_id}"
    else:
        redirect_url = "/summary/my-weekly"

    db.delete(activity)
    db.commit()

    return RedirectResponse(url=redirect_url, status_code=303)
