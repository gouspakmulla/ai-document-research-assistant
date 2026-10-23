from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.collection import Collection, CollectionDocument
from backend.app.schemas.collection import (
    CollectionResponse,
    CollectionCreateRequest,
    CollectionUpdateRequest,
)
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/collections", tags=["Collections"])

@router.get("", response_model=List[CollectionResponse])
async def list_collections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List collections belonging strictly to authenticated user."""
    query = select(Collection).where(Collection.user_id == current_user.id).order_by(Collection.created_at.desc())
    result = await db.execute(query)
    collections = result.scalars().all()

    # Populate document count for each collection
    resp = []
    for col in collections:
        count_query = select(func.count()).select_from(CollectionDocument).where(CollectionDocument.collection_id == col.id)
        count_res = await db.execute(count_query)
        doc_count = count_res.scalar() or 0

        resp.append(
            CollectionResponse(
                id=col.id,
                user_id=col.user_id,
                name=col.name,
                description=col.description,
                document_count=doc_count,
                created_at=col.created_at,
                updated_at=col.updated_at,
            )
        )
    return resp

@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    payload: CollectionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new collection for the authenticated user."""
    col = Collection(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(col)
    await db.commit()
    await db.refresh(col)

    return CollectionResponse(
        id=col.id,
        user_id=col.user_id,
        name=col.name,
        description=col.description,
        document_count=0,
        created_at=col.created_at,
        updated_at=col.updated_at,
    )

@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a collection, ensuring user ownership."""
    query = select(Collection).where(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    )
    result = await db.execute(query)
    col = result.scalars().first()
    if not col:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found or access denied."
        )
    await db.delete(col)
    await db.commit()
