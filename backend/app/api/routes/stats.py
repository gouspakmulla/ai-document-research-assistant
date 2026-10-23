from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.collection import Collection
from backend.app.models.conversation import Conversation
from backend.app.schemas.stats import DashboardStatsResponse
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Aggregate statistics for the authenticated user's library and research sessions."""
    # Total documents
    doc_q = select(func.count()).select_from(Document).where(Document.user_id == current_user.id)
    doc_res = await db.execute(doc_q)
    total_docs = doc_res.scalar() or 0

    # Total collections
    col_q = select(func.count()).select_from(Collection).where(Collection.user_id == current_user.id)
    col_res = await db.execute(col_q)
    total_cols = col_res.scalar() or 0

    # Total conversations
    conv_q = select(func.count()).select_from(Conversation).where(Conversation.user_id == current_user.id)
    conv_res = await db.execute(conv_q)
    total_convs = conv_res.scalar() or 0

    # Total pages indexed
    pages_q = (
        select(func.coalesce(func.sum(Document.page_count), 0))
        .where(
            Document.user_id == current_user.id,
            Document.processing_status == "READY"
        )
    )
    pages_res = await db.execute(pages_q)
    total_pages = pages_res.scalar() or 0

    return DashboardStatsResponse(
        total_documents=total_docs,
        total_collections=total_cols,
        total_conversations=total_convs,
        total_pages_indexed=total_pages
    )
