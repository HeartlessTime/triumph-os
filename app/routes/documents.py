import os
import uuid
import shutil
from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Opportunity, Document

router = APIRouter(prefix="/documents", tags=["documents"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50")) * 1024 * 1024


@router.post("/opportunity/{opp_id}/upload")
async def upload_document(
    request: Request,
    opp_id: int,
    file: UploadFile = File(...),
    name: str = Form(None),
    document_type: str = Form("other"),
    db: Session = Depends(get_db),
):
    """Upload a document to an opportunity."""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Create uploads directory if needed
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate unique filename
    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1] if "." in original_filename else ""
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Get file size
    file_size = os.path.getsize(file_path)

    # Create document record
    document = Document(
        opportunity_id=opp_id,
        name=name or original_filename,
        original_filename=original_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        document_type=document_type,
    )

    db.add(document)
    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.get("/{doc_id}/download")
async def download_document(
    request: Request, doc_id: int, db: Session = Depends(get_db)
):
    """Download a document."""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type or "application/octet-stream",
    )


@router.get("/{doc_id}/view")
async def view_document(request: Request, doc_id: int, db: Session = Depends(get_db)):
    """View a document inline (for PDFs, images)."""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Return file for inline viewing
    return FileResponse(
        path=document.file_path,
        media_type=document.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{document.original_filename}"'
        },
    )


@router.post("/{doc_id}/delete")
async def delete_document(request: Request, doc_id: int, db: Session = Depends(get_db)):
    """Delete a document."""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    opp_id = document.opportunity_id

    # Delete file from disk
    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    # Delete record
    db.delete(document)
    db.commit()

    return RedirectResponse(url=f"/opportunities/{opp_id}", status_code=303)


@router.post("/{doc_id}/update")
async def update_document(
    request: Request,
    doc_id: int,
    name: str = Form(...),
    document_type: str = Form("other"),
    db: Session = Depends(get_db),
):
    """Update document metadata."""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document.name = name
    document.document_type = document_type

    db.commit()

    return RedirectResponse(
        url=f"/opportunities/{document.opportunity_id}", status_code=303
    )
