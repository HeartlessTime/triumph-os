import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# LOAD ENV FIRST — MUST BE HERE
load_dotenv()

from app.routes import (
    dashboard_router,
    accounts_router,
    contacts_router,
    opportunities_router,
    estimates_router,
    documents_router,
    activities_router,
    tasks_router,
    guide_router,
    email_sync_router,
    estimators_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="RevenueOS",
        description="Sales & Estimating Platform",
        version="1.0.0",
    )

    os.makedirs("app/static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(dashboard_router)
    app.include_router(accounts_router)
    app.include_router(contacts_router)
    app.include_router(opportunities_router)
    app.include_router(estimates_router)
    app.include_router(documents_router)
    app.include_router(activities_router)
    app.include_router(tasks_router)
    app.include_router(guide_router)
    app.include_router(email_sync_router)
    app.include_router(estimators_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
