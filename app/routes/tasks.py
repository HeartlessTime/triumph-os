from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Opportunity, Task, User

router = APIRouter(prefix="/tasks", tags=["tasks"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/opportunity/{opp_id}/add")
async def add_task(
    request: Request,
    opp_id: int,
    title: str = Form(...),
    description: str = Form(None),
    due_date: str = Form(None),
    priority: str = Form("Medium"),
    assigned_to_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """Add a task to an opportunity."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    task = Task(
        opportunity_id=opp_id,
        title=title,
        description=description or None,
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None,
        priority=priority,
        assigned_to_id=assigned_to_id if assigned_to_id else None,
    )

    db.add(task)
    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.post("/{task_id}/complete")
async def complete_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Mark a task as complete."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.complete()
    db.commit()

    if task.opportunity_id:
        return RedirectResponse(url=f"/opportunities/{task.opportunity_id}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post("/{task_id}/reopen")
async def reopen_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Reopen a completed task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.reopen()
    db.commit()

    if task.opportunity_id:
        return RedirectResponse(url=f"/opportunities/{task.opportunity_id}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.get("/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_form(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Display edit task form."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()

    return templates.TemplateResponse("tasks/edit.html", {
        "request": request,
        "task": task,
        "users": users,
        "priorities": Task.PRIORITIES,
    })


@router.post("/{task_id}/edit")
async def update_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: str = Form(None),
    due_date: str = Form(None),
    priority: str = Form("Medium"),
    assigned_to_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """Update a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.title = title
    task.description = description or None
    task.due_date = datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None
    task.priority = priority
    task.assigned_to_id = assigned_to_id if assigned_to_id else None

    db.commit()

    if task.opportunity_id:
        return RedirectResponse(url=f"/opportunities/{task.opportunity_id}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post("/{task_id}/delete")
async def delete_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    opp_id = task.opportunity_id
    db.delete(task)
    db.commit()

    if opp_id:
        return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)
    return RedirectResponse(url="/", status_code=303)
