import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from app.routes import (
    auth_router,
    dashboard_router,
    accounts_router,
    contacts_router,
    opportunities_router,
    estimates_router,
    documents_router,
    activities_router,
    tasks_router,
)
from app.auth import get_current_user
from app.database import get_db


def create_app() -> FastAPI:
    """Application factory."""
    load_dotenv()

    # Create FastAPI app
    app = FastAPI(
        title="RevenueOS",
        description="Sales & Estimating Platform",
        version="1.0.0"
    )

    # Mount static files
    os.makedirs("app/static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Create uploads directory
    os.makedirs(os.getenv("UPLOAD_DIR", "./uploads"), exist_ok=True)

    # Include routers
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(accounts_router)
    app.include_router(contacts_router)
    app.include_router(opportunities_router)
    app.include_router(estimates_router)
    app.include_router(documents_router)
    app.include_router(activities_router)
    app.include_router(tasks_router)

    return app


app = create_app()


# Template globals
templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def add_user_to_templates(request: Request, call_next):
    """Add current user to all template contexts."""
    response = await call_next(request)
    return response


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return templates.TemplateResponse(
        "errors/404.html",
        {"request": request},
        status_code=404
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    """Handle 403 errors."""
    return templates.TemplateResponse(
        "errors/403.html",
        {"request": request},
        status_code=403
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Handle 500 errors."""
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request},
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
