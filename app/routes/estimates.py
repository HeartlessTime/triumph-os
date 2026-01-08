import os
import uuid
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import Opportunity, Estimate, EstimateLineItem, Document
from app.services.estimate import (
    recalculate_estimate, 
    get_next_version, 
    copy_estimate_to_new_version
)
from app.services.proposal import generate_proposal_pdf

router = APIRouter(prefix="/estimates", tags=["estimates"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")


@router.get("/opportunity/{opp_id}/new", response_class=HTMLResponse)
async def new_estimate_form(
    request: Request,
    opp_id: int,
    db: Session = Depends(get_db)
):
    """Display new estimate form."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/estimates/opportunity/{opp_id}/new", status_code=303)
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    next_version = get_next_version(opp_id, db)
    
    return templates.TemplateResponse("estimates/form.html", {
        "request": request,
        "user": user,
        "opportunity": opportunity,
        "estimate": None,
        "next_version": next_version,
        "line_types": EstimateLineItem.LINE_TYPES,
        "units": EstimateLineItem.UNITS,
        "statuses": Estimate.STATUSES,
        "is_new": True,
    })


@router.post("/opportunity/{opp_id}/new")
async def create_estimate(
    request: Request,
    opp_id: int,
    name: str = Form(None),
    margin_percent: str = Form("20"),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new estimate."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    next_version = get_next_version(opp_id, db)
    
    estimate = Estimate(
        opportunity_id=opp_id,
        version=next_version,
        name=name or None,
        margin_percent=Decimal(margin_percent) if margin_percent else Decimal("20"),
        notes=notes or None,
        created_by_id=user.id,
    )
    
    db.add(estimate)
    db.commit()
    
    return RedirectResponse(url=f"/estimates/{estimate.id}", status_code=303)


@router.get("/{estimate_id}", response_class=HTMLResponse)
async def view_estimate(
    request: Request,
    estimate_id: int,
    db: Session = Depends(get_db)
):
    """View and edit estimate with line items."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/estimates/{estimate_id}", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    return templates.TemplateResponse("estimates/view.html", {
        "request": request,
        "user": user,
        "estimate": estimate,
        "opportunity": estimate.opportunity,
        "line_types": EstimateLineItem.LINE_TYPES,
        "units": EstimateLineItem.UNITS,
        "statuses": Estimate.STATUSES,
    })


@router.post("/{estimate_id}/update")
async def update_estimate(
    request: Request,
    estimate_id: int,
    name: str = Form(None),
    status: str = Form(None),
    margin_percent: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update estimate header fields."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    if name is not None:
        estimate.name = name or None
    if status is not None:
        estimate.status = status
    if margin_percent is not None:
        estimate.margin_percent = Decimal(margin_percent) if margin_percent else Decimal("20")
    if notes is not None:
        estimate.notes = notes or None
    
    # Recalculate totals with new margin
    recalculate_estimate(estimate)
    
    db.commit()
    
    return RedirectResponse(url=f"/estimates/{estimate_id}", status_code=303)


@router.post("/{estimate_id}/line-items/add")
async def add_line_item(
    request: Request,
    estimate_id: int,
    line_type: str = Form(...),
    description: str = Form(...),
    quantity: str = Form("1"),
    unit: str = Form(None),
    unit_cost: str = Form("0"),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Add a line item to an estimate."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Get max sort order
    max_sort = db.query(EstimateLineItem.sort_order)\
        .filter(EstimateLineItem.estimate_id == estimate_id)\
        .order_by(EstimateLineItem.sort_order.desc())\
        .first()
    next_sort = (max_sort[0] + 1) if max_sort else 0
    
    # Parse values
    qty = Decimal(quantity) if quantity else Decimal("1")
    cost = Decimal(unit_cost) if unit_cost else Decimal("0")
    
    line_item = EstimateLineItem(
        estimate_id=estimate_id,
        line_type=line_type,
        description=description,
        quantity=qty,
        unit=unit or None,
        unit_cost=cost,
        total=qty * cost,
        sort_order=next_sort,
        notes=notes or None,
    )
    
    db.add(line_item)
    db.flush()
    
    # Recalculate estimate totals
    recalculate_estimate(estimate)
    
    db.commit()
    
    return RedirectResponse(url=f"/estimates/{estimate_id}", status_code=303)


@router.post("/{estimate_id}/line-items/{item_id}/update")
async def update_line_item(
    request: Request,
    estimate_id: int,
    item_id: int,
    line_type: str = Form(...),
    description: str = Form(...),
    quantity: str = Form("1"),
    unit: str = Form(None),
    unit_cost: str = Form("0"),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update a line item."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    line_item = db.query(EstimateLineItem).filter(
        EstimateLineItem.id == item_id,
        EstimateLineItem.estimate_id == estimate_id
    ).first()
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    # Update fields
    line_item.line_type = line_type
    line_item.description = description
    line_item.quantity = Decimal(quantity) if quantity else Decimal("1")
    line_item.unit = unit or None
    line_item.unit_cost = Decimal(unit_cost) if unit_cost else Decimal("0")
    line_item.notes = notes or None
    line_item.total = line_item.quantity * line_item.unit_cost
    
    # Recalculate estimate totals
    recalculate_estimate(estimate)
    
    db.commit()
    
    return RedirectResponse(url=f"/estimates/{estimate_id}", status_code=303)


@router.post("/{estimate_id}/line-items/{item_id}/delete")
async def delete_line_item(
    request: Request,
    estimate_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    """Delete a line item."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    line_item = db.query(EstimateLineItem).filter(
        EstimateLineItem.id == item_id,
        EstimateLineItem.estimate_id == estimate_id
    ).first()
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    db.delete(line_item)
    db.flush()
    
    # Recalculate estimate totals
    recalculate_estimate(estimate)
    
    db.commit()
    
    return RedirectResponse(url=f"/estimates/{estimate_id}", status_code=303)


@router.post("/{estimate_id}/copy")
async def copy_estimate(
    request: Request,
    estimate_id: int,
    db: Session = Depends(get_db)
):
    """Create a new version by copying this estimate."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    new_estimate = copy_estimate_to_new_version(estimate, db)
    new_estimate.created_by_id = user.id
    
    db.commit()
    
    return RedirectResponse(url=f"/estimates/{new_estimate.id}", status_code=303)


@router.post("/{estimate_id}/generate-proposal")
async def generate_proposal(
    request: Request,
    estimate_id: int,
    db: Session = Depends(get_db)
):
    """Generate a PDF proposal for this estimate."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    opportunity = estimate.opportunity
    
    # Create uploads directory if needed
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    filename = f"proposal_{opportunity.id}_v{estimate.version}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Generate the PDF
    generate_proposal_pdf(
        estimate=estimate,
        opportunity=opportunity,
        output_path=file_path
    )
    
    # Create document record
    file_size = os.path.getsize(file_path)
    
    document = Document(
        opportunity_id=opportunity.id,
        estimate_id=estimate.id,
        name=f"Proposal v{estimate.version}",
        original_filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        document_type="proposal",
        uploaded_by_id=user.id,
    )
    
    db.add(document)
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opportunity.id}", status_code=303)


@router.post("/{estimate_id}/delete")
async def delete_estimate(
    request: Request,
    estimate_id: int,
    db: Session = Depends(get_db)
):
    """Delete an estimate."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    opp_id = estimate.opportunity_id
    
    db.delete(estimate)
    db.commit()
    
    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)
