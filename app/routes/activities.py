from datetime import datetime, date
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import Opportunity, Activity, Contact
from app.services.followup import calculate_next_followup

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
    db: Session = Depends(get_db)
):
    """Add an activity to an opportunity."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Parse activity date
    if activity_date:
        activity_dt = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
    else:
        activity_dt = datetime.now()
    
    activity = Activity(
        opportunity_id=opp_id,
        activity_type=activity_type,
        subject=subject,
        description=description or None,
        activity_date=activity_dt,
        contact_id=contact_id if contact_id else None,
        created_by_id=user.id,
    )
    
    db.add(activity)
    
    # Update last_contacted if requested and activity is today or in the past
    if update_last_contacted and activity_dt.date() <= date.today():
        opportunity.last_contacted = activity_dt.date()
        # Recalculate followup
        opportunity.next_followup = calculate_next_followup(
            stage=opportunity.stage,
            last_contacted=opportunity.last_contacted,
            bid_date=opportunity.bid_date
        )
    
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.get("/{activity_id}/edit", response_class=HTMLResponse)
async def edit_activity_form(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db)
):
    """Display edit activity form."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    contacts = db.query(Contact).filter(
        Contact.account_id == activity.opportunity.account_id
    ).order_by(Contact.last_name).all()
    
    return templates.TemplateResponse("activities/edit.html", {
        "request": request,
        "user": user,
        "activity": activity,
        "contacts": contacts,
        "activity_types": Activity.ACTIVITY_TYPES,
    })


@router.post("/{activity_id}/edit")
async def update_activity(
    request: Request,
    activity_id: int,
    activity_type: str = Form(...),
    subject: str = Form(...),
    description: str = Form(None),
    activity_date: str = Form(...),
    contact_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """Update an activity."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    activity.activity_type = activity_type
    activity.subject = subject
    activity.description = description or None
    activity.activity_date = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
    activity.contact_id = contact_id if contact_id else None
    
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{activity.opportunity_id}", status_code=303)


@router.post("/{activity_id}/delete")
async def delete_activity(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db)
):
    """Delete an activity."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    opp_id = activity.opportunity_id
    db.delete(activity)
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)
