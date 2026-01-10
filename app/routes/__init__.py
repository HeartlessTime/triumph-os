from app.routes.dashboard import router as dashboard_router
from app.routes.accounts import router as accounts_router
from app.routes.contacts import router as contacts_router
from app.routes.opportunities import router as opportunities_router
from app.routes.estimates import router as estimates_router
from app.routes.documents import router as documents_router
from app.routes.activities import router as activities_router
from app.routes.tasks import router as tasks_router
from app.routes.guide import router as guide_router
from app.routes.email_sync import router as email_sync_router
from app.routes.estimators import router as estimators_router
from app.routes.summary import router as summary_router
from app.routes.today import router as today_router

__all__ = [
    "dashboard_router",
    "accounts_router",
    "contacts_router",
    "opportunities_router",
    "estimates_router",
    "documents_router",
    "activities_router",
    "tasks_router",
    "guide_router",
    "email_sync_router",
    "estimators_router",
    "summary_router",
    "today_router",
]
