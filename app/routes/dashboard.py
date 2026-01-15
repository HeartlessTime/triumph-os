from datetime import date
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dashboard_service import get_dashboard_data
from app.template_config import templates

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    data = get_dashboard_data(db, today)

    return templates.TemplateResponse(
        "dashboard/index.html", {"request": request, **data}
    )
