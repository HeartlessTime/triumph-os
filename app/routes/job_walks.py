"""
Job Walks Routes

Handles creation and management of job walk activities.
Job walks are structured handoffs from field to estimator, with
walk notes (transcript) and optional area breakdowns.
"""

import re
from datetime import datetime, date
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Activity, WalkSegment, Account, Contact
from app.template_config import templates
from app.utils.safe_redirect import safe_redirect_url

router = APIRouter(prefix="/job-walks", tags=["job_walks"])


def utc_now():
    return datetime.utcnow()


@router.get("", response_class=HTMLResponse)
async def job_walks_list(
    request: Request,
    db: Session = Depends(get_db),
):
    """List all job walks: open and completed."""
    all_walks = (
        db.query(Activity)
        .options(
            selectinload(Activity.contact).selectinload(Contact.account),
            selectinload(Activity.walk_segments),
        )
        .filter(Activity.activity_type == "job_walk")
        .order_by(Activity.activity_date.desc())
        .all()
    )

    open_walks = [w for w in all_walks if w.job_walk_status != "complete"]
    completed_walks = [w for w in all_walks if w.job_walk_status == "complete"]

    # Data for job walk modal
    all_accounts = db.query(Account).order_by(Account.name).all()
    all_contacts = (
        db.query(Contact)
        .options(selectinload(Contact.account))
        .order_by(Contact.last_name, Contact.first_name)
        .all()
    )

    return templates.TemplateResponse(
        "job_walks/list.html",
        {
            "request": request,
            "open_walks": open_walks,
            "completed_walks": completed_walks,
            "all_accounts": all_accounts,
            "all_contacts": all_contacts,
        },
    )


@router.post("/start")
async def start_job_walk(
    request: Request,
    subject: str = Form(...),
    account_id: int = Form(...),
    activity_date: str = Form(None),
    contact_id: int = Form(None),
    description: str = Form(None),
    technicians_needed: int = Form(None),
    estimated_man_hours: int = Form(None),
    db: Session = Depends(get_db),
):
    """Create a job walk activity and redirect to the walk page."""
    current_user = request.state.current_user
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=400, detail="Account not found")

    if activity_date:
        activity_dt = datetime.strptime(activity_date, "%Y-%m-%dT%H:%M")
    else:
        activity_dt = utc_now()

    activity = Activity(
        activity_type="job_walk",
        subject=subject,
        description=description or None,
        activity_date=activity_dt,
        contact_id=contact_id if contact_id else None,
        created_by_id=current_user.id,
        job_walk_status="open",
        technicians_needed=technicians_needed if technicians_needed else None,
        estimated_man_hours=estimated_man_hours if estimated_man_hours else None,
    )

    db.add(activity)
    db.commit()

    return RedirectResponse(url=f"/job-walks/{activity.id}", status_code=303)


@router.get("/{activity_id}", response_class=HTMLResponse)
async def walk_page(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db),
):
    """Job walk editor page."""
    activity = (
        db.query(Activity)
        .options(
            selectinload(Activity.walk_segments),
            selectinload(Activity.contact).selectinload(Contact.account),
        )
        .filter(Activity.id == activity_id, Activity.activity_type == "job_walk")
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Job walk not found")

    return_to = safe_redirect_url(request.query_params.get("from"), "/job-walks")

    return templates.TemplateResponse(
        "job_walks/walk.html",
        {
            "request": request,
            "activity": activity,
            "segments": activity.walk_segments,
            "return_to": return_to,
        },
    )


@router.post("/{activity_id}/segments")
async def add_segment(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db),
):
    """Add a new area to a job walk. Returns JSON."""
    activity = (
        db.query(Activity)
        .filter(Activity.id == activity_id, Activity.activity_type == "job_walk")
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Job walk not found")

    payload = await request.json()

    # Determine next sort_order
    max_order = (
        db.query(WalkSegment.sort_order)
        .filter(WalkSegment.activity_id == activity_id)
        .order_by(WalkSegment.sort_order.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order else 0

    segment = WalkSegment(
        activity_id=activity_id,
        location_name=str(payload.get("location_name", "")).strip() or "New Area",
        segment_type="other",
        description=str(payload.get("description", "")).strip() or None,
        quantity_label=str(payload.get("quantity_label", "")).strip() or None,
        estimated_cable_length=_parse_int(payload.get("estimated_cable_length")),
        sort_order=next_order,
    )
    db.add(segment)
    db.commit()

    return JSONResponse({
        "success": True,
        "segment": _segment_dict(segment),
    })


@router.post("/{activity_id}/segments/{segment_id}")
async def update_segment(
    request: Request,
    activity_id: int,
    segment_id: int,
    db: Session = Depends(get_db),
):
    """Auto-save an area field. Returns JSON."""
    segment = (
        db.query(WalkSegment)
        .filter(WalkSegment.id == segment_id, WalkSegment.activity_id == activity_id)
        .first()
    )
    if not segment:
        raise HTTPException(status_code=404, detail="Area not found")

    payload = await request.json()

    ALLOWED_FIELDS = {
        "location_name", "description",
        "quantity_label", "estimated_cable_length",
    }

    for field, value in payload.items():
        if field not in ALLOWED_FIELDS:
            continue
        if field == "estimated_cable_length":
            setattr(segment, field, _parse_int(value))
        elif field == "location_name":
            val = str(value).strip()
            if val:
                setattr(segment, field, val)
        else:
            setattr(segment, field, str(value).strip() or None)

    db.commit()
    return JSONResponse({"status": "saved"})


@router.post("/{activity_id}/segments/{segment_id}/delete")
async def delete_segment(
    request: Request,
    activity_id: int,
    segment_id: int,
    db: Session = Depends(get_db),
):
    """Delete an area. Returns JSON."""
    segment = (
        db.query(WalkSegment)
        .filter(WalkSegment.id == segment_id, WalkSegment.activity_id == activity_id)
        .first()
    )
    if not segment:
        raise HTTPException(status_code=404, detail="Area not found")

    db.delete(segment)
    db.commit()
    return JSONResponse({"success": True})


@router.post("/{activity_id}/update-status")
async def update_job_walk_status(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db),
):
    """Update job walk status. Also syncs estimate_completed fields."""
    activity = (
        db.query(Activity)
        .filter(Activity.id == activity_id, Activity.activity_type == "job_walk")
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Job walk not found")

    payload = await request.json()
    new_status = payload.get("status")

    if new_status not in ("open", "sent_to_estimator", "complete"):
        raise HTTPException(status_code=400, detail="Invalid status")

    activity.job_walk_status = new_status

    # Sync legacy fields
    if new_status == "complete":
        activity.estimate_completed = True
        if not activity.estimate_completed_at:
            activity.estimate_completed_at = date.today()
    else:
        activity.estimate_completed = False
        activity.estimate_completed_at = None

    db.commit()
    return JSONResponse({"success": True, "status": new_status})


@router.get("/{activity_id}/summary", response_class=HTMLResponse)
async def walk_summary(
    request: Request,
    activity_id: int,
    db: Session = Depends(get_db),
):
    """Estimator summary page with copy-to-clipboard."""
    activity = (
        db.query(Activity)
        .options(
            selectinload(Activity.walk_segments),
            selectinload(Activity.contact).selectinload(Contact.account),
        )
        .filter(Activity.id == activity_id, Activity.activity_type == "job_walk")
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Job walk not found")

    summary_text = _build_summary_text(activity)

    return templates.TemplateResponse(
        "job_walks/summary.html",
        {
            "request": request,
            "activity": activity,
            "summary_text": summary_text,
        },
    )


def _parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _segment_dict(segment):
    return {
        "id": segment.id,
        "location_name": segment.location_name,
        "description": segment.description,
        "quantity_label": segment.quantity_label,
        "estimated_cable_length": segment.estimated_cable_length,
    }


def _build_summary_text(activity):
    lines = []
    lines.append("JOB WALK SUMMARY")
    lines.append("=================")
    lines.append(f"Date: {activity.activity_date.strftime('%b %d, %Y')}")

    # Account
    account_name = None
    if activity.contact and activity.contact.account:
        account_name = activity.contact.account.name
    lines.append(f"Account: {account_name or '—'}")

    if activity.contact:
        lines.append(f"Contact: {activity.contact.full_name}")
    lines.append(f"Purpose: {activity.subject}")
    if activity.technicians_needed:
        lines.append(f"Technicians Needed: {activity.technicians_needed}")
    if activity.estimated_man_hours:
        lines.append(f"Estimated Man Hours: {activity.estimated_man_hours}")
    lines.append("")

    # Walk notes (main content)
    if activity.walk_notes:
        lines.append("WALK NOTES")
        lines.append("----------")
        lines.append(activity.walk_notes.strip())
        lines.append("")

    # Areas
    segments = activity.walk_segments
    if segments:
        lines.append("AREAS")
        lines.append("-----")
        total_cable = 0
        total_drops = 0
        for i, seg in enumerate(segments, 1):
            lines.append(f"{i}. {seg.location_name}")
            if seg.quantity_label:
                lines.append(f"   Qty: {seg.quantity_label}")
                # Parse leading number from quantity_label (e.g. "48 drops", "48")
                qty_match = re.match(r"(\d+)", seg.quantity_label.strip())
                if qty_match:
                    total_drops += int(qty_match.group(1))
            if seg.estimated_cable_length:
                lines.append(f"   Cable: {seg.estimated_cable_length} ft")
                total_cable += seg.estimated_cable_length
            if seg.description:
                lines.append(f"   Notes: {seg.description}")
            lines.append("")

        if total_cable > 0 or total_drops > 0:
            lines.append("TOTALS")
            lines.append("------")
            if total_cable > 0:
                lines.append(f"Total Cable: {total_cable} ft")
            if total_drops > 0:
                lines.append(f"Total Data Drops: {total_drops}")
            lines.append("")

    return "\n".join(lines)
