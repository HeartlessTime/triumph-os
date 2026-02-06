from app.routes.dashboard import router as dashboard_router
from app.routes.accounts import router as accounts_router
from app.routes.contacts import router as contacts_router
from app.routes.opportunities import router as opportunities_router
from app.routes.estimates import router as estimates_router
from app.routes.activities import router as activities_router
from app.routes.tasks import router as tasks_router
from app.routes.guide import router as guide_router
from app.routes.estimators import router as estimators_router
from app.routes.summary import router as summary_router
from app.routes.today import router as today_router
from app.routes.audit_log import router as audit_log_router
from app.routes.job_walks import router as job_walks_router
from app.routes.commissions import router as commissions_router
from app.routes.daily_summary import router as daily_summary_router

__all__ = [
    "dashboard_router",
    "accounts_router",
    "contacts_router",
    "opportunities_router",
    "estimates_router",
    "activities_router",
    "tasks_router",
    "guide_router",
    "estimators_router",
    "summary_router",
    "today_router",
    "audit_log_router",
    "job_walks_router",
    "commissions_router",
    "daily_summary_router",
]
