from datetime import date
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dashboard_service import get_dashboard_data

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    data = get_dashboard_data(db, today)

    return templates.TemplateResponse(
        "dashboard/index.html", {"request": request, **data}
    )
