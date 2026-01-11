"""
Authentication routes for login/logout.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.utils import authenticate_user

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display the login form."""
    # If already logged in, redirect to dashboard
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "error": None,
        },
    )


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Process login form submission."""
    user = authenticate_user(db, email, password)

    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "Invalid email or password",
            },
            status_code=401,
        )

    # Set user_id in session
    request.session["user_id"] = user.id

    # Redirect to dashboard or originally requested page
    next_url = request.query_params.get("next", "/")
    return RedirectResponse(url=next_url, status_code=303)


@router.post("/logout")
async def logout(request: Request):
    """Log out the current user."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
async def logout_get(request: Request):
    """Log out via GET (for convenience)."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
