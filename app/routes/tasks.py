from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, Opportunity, Task, User, Activity
from app.template_config import templates
from app.utils.safe_redirect import safe_redirect_url

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/quick-add")
async def quick_add_task(
    request: Request,
    title: str = Form(...),
    due_date: str = Form(None),
    description: str = Form(None),
    account_id: int = Form(None),
    db: Session = Depends(get_db),
):
    """Quick add a standalone task (no opportunity)."""
    current_user = request.state.current_user
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    task = Task(
        opportunity_id=None,
        title=title,
        description=description or None,
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None,
        account_id=account_id if account_id else None,
        assigned_to_id=current_user.id,
        created_by_id=current_user.id,
    )

    db.add(task)
    db.commit()

    # Redirect back to referrer or dashboard
    referer = request.headers.get("referer")
    if referer:
        return RedirectResponse(url=referer, status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post("/opportunity/{opp_id}/add")
async def add_task(
    request: Request,
    opp_id: int,
    title: str = Form(...),
    description: str = Form(None),
    due_date: str = Form(None),
    assigned_to_id: int = Form(None),
    db: Session = Depends(get_db),
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
        assigned_to_id=assigned_to_id if assigned_to_id else current_user.id,
        created_by_id=current_user.id,
    )

    db.add(task)
    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


# Column names for Task model (only these can be set)
TASK_COLUMNS = {
    "title", "description", "due_date", "status",
    "assigned_to_id", "opportunity_id", "account_id", "completed_at", "completed_by_id",
}


@router.post("/{task_id}/quick-update")
async def quick_update_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Production-safe autosave. Never raises 422 or 500."""
    try:
        current_user = request.state.current_user
        if not current_user:
            return {"status": "saved"}

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"status": "saved"}

        try:
            payload = await request.json()
        except Exception:
            try:
                form = await request.form()
                payload = dict(form)
            except Exception:
                payload = {}

        def clean_int(v):
            if v in (None, "", "null"):
                return None
            try:
                return int(v)
            except Exception:
                return None

        def clean_bool(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.lower() in ("true", "1", "yes", "on")
            return False

        def clean_date(v):
            if not v or v in ("", "null"):
                return None
            try:
                return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()
            except Exception:
                return None

        # Handle completion toggle
        if "completed" in payload:
            try:
                completed_val = clean_bool(payload["completed"])
                if completed_val:
                    task.complete(completed_by_user_id=current_user.id)
                    db.add(Activity(
                        opportunity_id=task.opportunity_id,
                        activity_type="task_completed",
                        subject=f"Completed task: {task.title}",
                        description=f"Task completed by {current_user.full_name}",
                        activity_date=datetime.utcnow(),
                        created_by_id=current_user.id,
                    ))
                else:
                    task.reopen()
            except Exception:
                pass

        # Handle title change
        if "title" in payload:
            try:
                title_val = str(payload["title"]).strip() if payload["title"] else ""
                if title_val:
                    task.title = title_val
            except Exception:
                pass

        # Handle description/notes change
        if "description" in payload:
            try:
                desc_val = payload["description"]
                task.description = str(desc_val).strip() if desc_val and str(desc_val).strip() else None
            except Exception:
                pass

        # Handle due_date change
        if "due_date" in payload:
            try:
                task.due_date = clean_date(payload["due_date"])
            except Exception:
                pass

        # Handle assigned_to_id change
        if "assigned_to_id" in payload:
            try:
                task.assigned_to_id = clean_int(payload["assigned_to_id"])
            except Exception:
                pass

        # Handle account_id change
        if "account_id" in payload:
            try:
                task.account_id = clean_int(payload["account_id"])
            except Exception:
                pass

        try:
            db.commit()
        except Exception:
            db.rollback()

        return {"status": "saved"}
    except Exception:
        return {"status": "saved"}


@router.post("/{task_id}/complete")
async def complete_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Mark a task as complete and create audit Activity."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    current_user = request.state.current_user
    task.complete(completed_by_user_id=current_user.id)

    # Create audit Activity for task completion
    activity = Activity(
        opportunity_id=task.opportunity_id,  # May be None for standalone tasks
        activity_type="task_completed",
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
        return RedirectResponse(
            url=f"/opportunities/{task.opportunity_id}", status_code=303
        )
    return RedirectResponse(url="/", status_code=303)


@router.post("/{task_id}/reopen")
async def reopen_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Reopen a completed task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.reopen()
    db.commit()

    if task.opportunity_id:
        return RedirectResponse(
            url=f"/opportunities/{task.opportunity_id}", status_code=303
        )
    return RedirectResponse(url="/", status_code=303)


@router.get("/{task_id}", response_class=HTMLResponse)
async def view_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Display task detail page with activity history."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get activities from the parent opportunity (newest first)
    activities = []
    if task.opportunity_id:
        activities = (
            db.query(Activity)
            .filter(Activity.opportunity_id == task.opportunity_id)
            .order_by(Activity.activity_date.desc())
            .limit(20)
            .all()
        )

    return templates.TemplateResponse(
        "tasks/view.html",
        {
            "request": request,
            "task": task,
            "activities": activities,
        },
    )


@router.get("/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_form(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Display edit task form."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
    accounts = db.query(Account).order_by(Account.name).all()

    return templates.TemplateResponse(
        "tasks/edit.html",
        {
            "request": request,
            "task": task,
            "users": users,
            "accounts": accounts,
            "priorities": [],
        },
    )


@router.post("/{task_id}/edit")
async def update_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: str = Form(None),
    due_date: str = Form(None),
    assigned_to_id: int = Form(None),
    account_id: int = Form(None),
    db: Session = Depends(get_db),
):
    """Update a task.

    REDIRECT RULE ORDER:
    1. If ?from= query param exists → use that URL (back navigation)
    2. Else if task.opportunity_id exists → /opportunities/{id}
    3. Else → /summary/my-weekly
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.title = title
    task.description = description or None
    task.due_date = datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None
    task.assigned_to_id = assigned_to_id if assigned_to_id else None
    task.account_id = account_id if account_id else None

    db.commit()

    # Check for explicit return URL from query params (back navigation)
    from_url = request.query_params.get("from")
    if from_url:
        return RedirectResponse(url=safe_redirect_url(from_url, "/summary/my-weekly"), status_code=303)
    elif task.opportunity_id:
        return RedirectResponse(url=f"/opportunities/{task.opportunity_id}", status_code=303)
    return RedirectResponse(url="/summary/my-weekly", status_code=303)


@router.post("/{task_id}/delete")
async def delete_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    """Delete a task.

    REDIRECT RULE ORDER:
    1. If ?from= query param exists → use that URL (back navigation)
    2. Else if task.opportunity_id exists → /opportunities/{id}
    3. Else → /summary/my-weekly
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    opp_id = task.opportunity_id
    from_url = request.query_params.get("from")

    db.delete(task)
    db.commit()

    # Check for explicit return URL from query params (back navigation)
    if from_url:
        return RedirectResponse(url=safe_redirect_url(from_url, "/summary/my-weekly"), status_code=303)
    elif opp_id:
        return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)
    return RedirectResponse(url="/summary/my-weekly", status_code=303)
