import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# LOAD ENV FIRST — MUST BE HERE
load_dotenv()

from app.routes import (
    dashboard_router,
    accounts_router,
    contacts_router,
    opportunities_router,
    estimates_router,
    activities_router,
    tasks_router,
    guide_router,
    estimators_router,
    summary_router,
    today_router,
    audit_log_router,
    job_walks_router,
    commissions_router,
    daily_summary_router,
)
from app.routes.auth import router as auth_router
from app.database import SessionLocal
from app.models import User


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to redirect unauthenticated users and inject current_user."""

    async def dispatch(self, request: Request, call_next):
        # Public paths that don't require authentication
        public_paths = ["/login", "/logout", "/static"]

        path = request.url.path

        # Initialize current_user as None
        request.state.current_user = None

        # Allow public paths
        if any(path.startswith(p) for p in public_paths):
            return await call_next(request)

        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            # Redirect to login with next parameter
            return RedirectResponse(url=f"/login?next={path}", status_code=303)

        # Fetch and store current user on request.state
        db = SessionLocal()
        try:
            user = (
                db.query(User)
                .filter(User.id == user_id, User.is_active == True)
                .first()
            )
            if not user:
                # User was deleted or deactivated
                request.session.clear()
                return RedirectResponse(url="/login", status_code=303)
            request.state.current_user = user
        finally:
            db.close()

        return await call_next(request)


def create_app() -> FastAPI:
    app = FastAPI(
        title="RevenueOS",
        description="Sales & Estimating Platform",
        version="1.0.0",
    )

    # Session middleware for cookie-based sessions
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError("SECRET_KEY environment variable is required")

    # MIDDLEWARE ORDER MATTERS: Added last runs first (outermost)
    # We want: Request -> SessionMiddleware -> AuthMiddleware -> Route
    # So we add AuthMiddleware first, then SessionMiddleware
    app.add_middleware(AuthMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie="triumph_session",
        max_age=60 * 60 * 24 * 7,  # 7 days
        same_site="lax",
        https_only=os.getenv("HTTPS_ONLY", "false").lower() == "true",
    )

    os.makedirs("app/static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Auth routes (login/logout) - no protection needed
    app.include_router(auth_router)

    # Protected routes
    app.include_router(dashboard_router)
    app.include_router(accounts_router)
    app.include_router(contacts_router)
    app.include_router(opportunities_router)
    app.include_router(estimates_router)
    app.include_router(activities_router)
    app.include_router(tasks_router)
    app.include_router(guide_router)
    app.include_router(estimators_router)
    app.include_router(summary_router)
    app.include_router(today_router)
    app.include_router(audit_log_router)
    app.include_router(job_walks_router)
    app.include_router(commissions_router)
    app.include_router(daily_summary_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")

    uvicorn.run(
        "app.main:app",
        host=host,  # nosec B104
        port=port,
        reload=True,
    )
