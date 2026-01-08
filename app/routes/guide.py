"""How-to guide routes."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["guide"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/how-to-use", response_class=HTMLResponse)
async def how_to_use(request: Request):
    """Display how-to-use guide page."""
    return templates.TemplateResponse("guide/how_to_use.html", {
        "request": request,
    })
