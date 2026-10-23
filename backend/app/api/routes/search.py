from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.collection import Collection
from backend.app.api.dependencies import get_current_user
from backend.app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from backend.app.services.retrieval_service import retrieval_service

router = APIRouter(prefix="/search", tags=["Semantic Search"])


@router.post("", response_model=SearchResponse)
async def semantic_search(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Semantic vector search across user documents with pgvector."""
    # 1. Validate optional document scope
    if payload.document_id:
        doc_q = select(Document).where(
            Document.id == payload.document_id,
            Document.user_id == current_user.id,
        )
        doc_res = await db.execute(doc_q)
        doc = doc_res.scalars().first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied.",
            )
        if doc.processing_status != "READY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document '{doc.filename}' cannot be searched because its status is '{doc.processing_status}'.",
            )

    # 2. Validate optional collection scope
    if payload.collection_id:
        col_q = select(Collection).where(
            Collection.id == payload.collection_id,
            Collection.user_id == current_user.id,
        )
        col_res = await db.execute(col_q)
        col = col_res.scalars().first()
        if not col:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found or access denied.",
            )

    # 3. Perform retrieval
    results = await retrieval_service.search(
        db=db,
        user_id=current_user.id,
        query=payload.query,
        document_id=payload.document_id,
        collection_id=payload.collection_id,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
    )

    items = [
        SearchResultItem(
            document_id=r.document_id,
            filename=r.filename,
            chunk_id=r.chunk_id,
            page_number=r.page_number,
            snippet=r.snippet,
            relevance_score=r.relevance_score,
        )
        for r in results
    ]

    return SearchResponse(
        query=payload.query,
        total_results=len(items),
        results=items,
    )
