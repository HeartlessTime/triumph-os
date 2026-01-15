"""How-to guide routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.template_config import templates

router = APIRouter(tags=["guide"])


@router.get("/how-to-use", response_class=HTMLResponse)
async def how_to_use(request: Request):
    """Display how-to-use guide page."""
    return templates.TemplateResponse(
        "guide/how_to_use.html",
        {
            "request": request,
        },
    )
