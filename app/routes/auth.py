from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import (
    authenticate_user, 
    set_session_cookie, 
    clear_session_cookie,
    get_current_user
)
from app.models.user import User

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str = "/",
    error: str = None,
    db: Session = Depends(get_db)
):
    """Display login page."""
    # Check if already logged in
    user = await get_current_user(request, db)
    if user:
        return RedirectResponse(url=next, status_code=303)
    
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "next": next,
        "error": error,
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db)
):
    """Process login form."""
    user = authenticate_user(db, email, password)
    
    if not user:
        return RedirectResponse(
            url=f"/login?error=Invalid+email+or+password&next={next}",
            status_code=303
        )
    
    response = RedirectResponse(url=next, status_code=303)
    set_session_cookie(response, user.id)
    return response


@router.get("/logout")
async def logout(request: Request):
    """Log out the current user."""
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Display user profile page."""
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/profile", status_code=303)
    
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "user": user,
    })
