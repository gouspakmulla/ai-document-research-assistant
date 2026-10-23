from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.schemas.document import (
    DocumentResponse,
    DocumentRenameRequest,
    DocumentChunkResponse,
)
from backend.app.api.dependencies import get_current_user
from backend.app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Secure PDF upload and automatic ingestion processing."""
    doc = await document_service.ingest_uploaded_file(
        file=file,
        user_id=current_user.id,
        db=db,
    )
    return doc


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents belonging strictly to the authenticated user."""
    query = select(Document).where(Document.user_id == current_user.id)
    if search:
        query = query.where(Document.filename.ilike(f"%{search.strip()}%"))
    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single document with strict user tenant check."""
    return await document_service.get_user_document(
        document_id=document_id,
        user_id=current_user.id,
        db=db,
    )


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream authenticated PDF document file with inline disposition."""
    doc, content = await document_service.get_document_content(
        document_id=document_id,
        user_id=current_user.id,
        db=db,
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve indexed chunks with page numbers for document citations."""
    return await document_service.get_document_chunks(
        document_id=document_id,
        user_id=current_user.id,
        db=db,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete document with disk and database cascade cleanup."""
    await document_service.delete_user_document(
        document_id=document_id,
        user_id=current_user.id,
        db=db,
    )


@router.patch("/{document_id}/rename", response_model=DocumentResponse)
async def rename_document(
    document_id: str,
    payload: DocumentRenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename user's document."""
    doc = await document_service.get_user_document(
        document_id=document_id,
        user_id=current_user.id,
        db=db,
    )
    doc.filename = payload.filename.strip()
    await db.commit()
    await db.refresh(doc)
    return doc
