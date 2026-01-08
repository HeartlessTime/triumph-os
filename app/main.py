import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

from app.routes import (
    auth_router,
    dashboard_router,
    accounts_router,
    contacts_router,
    opportunities_router,
    documents_router,
    activities_router,
    tasks_router,
)
from app.auth import get_current_user
from app.database import get_db, init_db, DATABASE_URL
import json

# Create FastAPI app
app = FastAPI(
    title="Triumph OS",
    description="Sales platform",
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
app.include_router(documents_router)
app.include_router(activities_router)
app.include_router(tasks_router)


# Template globals
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    """Ensure DB is reachable and initialized at startup. Will create tables
    automatically when using the default SQLite dev DB. If initialization
    fails the app will raise and stop with a clear error message.
    """
    try:
        # init_db will raise RuntimeError on failure
        init_db()
    except Exception as e:
        # Re-raise as RuntimeError so the server fails loudly
        raise RuntimeError(
            f"Database initialization failed for DATABASE_URL={DATABASE_URL}: {e}"
        ) from e


@app.middleware("http")
async def add_user_to_templates(request: Request, call_next):
    """Add current user to all template contexts."""
    response = await call_next(request)
    return response


@app.middleware("http")
async def inject_default_probability(request: Request, call_next):
    """Inject a default probability into JSON request bodies when missing.

    This prevents Pydantic/FastAPI from rejecting requests that don't include
    a `probability` field in the JSON body (some clients POST JSON).
    """
    try:
        if request.method in ("POST", "PUT", "PATCH"):
            ctype = request.headers.get("content-type", "")
            if "application/json" in ctype:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        payload = json.loads(body_bytes)
                    except Exception:
                        payload = None
                    if isinstance(payload, dict) and "probability" not in payload:
                        payload["probability"] = 0
                        new_body = json.dumps(payload).encode("utf-8")
                        async def receive():
                            return {"type": "http.request", "body": new_body}
                        request = Request(request.scope, receive)
    except Exception:
        # If anything goes wrong here, continue without injection.
        pass

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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
