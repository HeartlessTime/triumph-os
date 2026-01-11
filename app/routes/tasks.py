from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Opportunity, Task, User, Activity

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

    current_user = request.state.current_user
    task = Task(
        opportunity_id=opp_id,
        title=title,
        description=description or None,
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None,
        priority=priority,
        assigned_to_id=assigned_to_id if assigned_to_id else current_user.id,
        created_by_id=current_user.id,
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
    """Mark a task as complete and create audit Activity."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    current_user = request.state.current_user
    task.complete(completed_by_user_id=current_user.id)

    # Create audit Activity for task completion
    activity = Activity(
        opportunity_id=task.opportunity_id,  # May be None for standalone tasks
        activity_type='task_completed',
        subject=f"Completed task: {task.title}",
        description=f"Task completed by {current_user.full_name}",
        activity_date=datetime.utcnow(),
        created_by_id=current_user.id,
    )
    db.add(activity)
    db.commit()

    # Redirect back to referrer or default location
    referer = request.headers.get("referer")
    if referer:
        return RedirectResponse(url=referer, status_code=303)
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


@router.get("/{task_id}", response_class=HTMLResponse)
async def view_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Display task detail page with activity history."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get activities from the parent opportunity (newest first)
    activities = []
    if task.opportunity_id:
        activities = db.query(Activity).filter(
            Activity.opportunity_id == task.opportunity_id
        ).order_by(Activity.activity_date.desc()).limit(20).all()

    return templates.TemplateResponse("tasks/view.html", {
        "request": request,
        "task": task,
        "activities": activities,
    })


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
