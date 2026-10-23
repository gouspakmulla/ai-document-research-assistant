import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.conversation import Conversation, Message
from backend.app.models.collection import Collection
from backend.app.models.citation import MessageCitation
from backend.app.models.document import Document
from backend.app.schemas.chat import (
    ConversationResponse,
    ConversationCreateRequest,
    MessageResponse,
    CitationResponse,
    AskQuestionRequest,
    AskQuestionResponse,
)
from backend.app.api.dependencies import get_current_user, require_csrf
from backend.app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat & Conversations"])


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List conversations belonging strictly to current user."""
    query = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(query)
    convs = result.scalars().all()

    resp = []
    for c in convs:
        # Message count
        count_q = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == c.id)
        )
        count_res = await db.execute(count_q)
        msg_count = count_res.scalar() or 0

        # Collection name if applicable
        col_name = None
        if c.collection_id:
            col_q = select(Collection.name).where(Collection.id == c.collection_id)
            col_res = await db.execute(col_q)
            col_name = col_res.scalar()

        resp.append(
            ConversationResponse(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                collection_id=c.collection_id,
                collection_name=col_name,
                message_count=msg_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return resp


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation session for current user."""
    # If collection_id provided, verify user ownership
    col_name = None
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
        col_name = col.name

    conv = Conversation(
        user_id=current_user.id,
        title=payload.title.strip() if payload.title else "New Research Inquiry",
        collection_id=payload.collection_id,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        collection_id=conv.collection_id,
        collection_name=col_name,
        message_count=0,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a single conversation owned by the authenticated user."""
    conv_q = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    )
    conv_res = await db.execute(conv_q)
    conv = conv_res.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    count_q = (
        select(func.count())
        .select_from(Message)
        .where(Message.conversation_id == conv.id)
    )
    count_res = await db.execute(count_q)
    msg_count = count_res.scalar() or 0

    col_name = None
    if conv.collection_id:
        col_q = select(Collection.name).where(Collection.id == conv.collection_id)
        col_res = await db.execute(col_q)
        col_name = col_res.scalar()

    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        collection_id=conv.collection_id,
        collection_name=col_name,
        message_count=msg_count,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete conversation ensuring strict tenant isolation."""
    query = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    )
    result = await db.execute(query)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )
    await db.delete(conv)
    await db.commit()


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
)
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages and citations in a conversation with tenant verification."""
    # Verify conversation ownership
    conv_q = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    )
    conv_res = await db.execute(conv_q)
    conv = conv_res.scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    # Fetch messages with citations
    msg_q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(selectinload(Message.citations))
        .order_by(Message.created_at.asc())
    )
    msg_res = await db.execute(msg_q)
    messages = msg_res.scalars().all()

    resp = []
    for m in messages:
        cits = [
            CitationResponse(
                id=c.id,
                message_id=c.message_id,
                document_id=c.document_id,
                chunk_id=c.chunk_id,
                document_name=c.document_name,
                page_number=c.page_number,
                snippet=c.snippet,
                relevance_score=c.relevance_score,
                created_at=c.created_at,
            )
            for c in m.citations
        ]
        resp.append(
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                citations=cits,
            )
        )
    return resp


@router.post(
    "/ask",
    response_model=AskQuestionResponse,
    dependencies=[Depends(require_csrf)],
)
async def ask_question(
    payload: AskQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG inquiry endpoint grounded in authorized user documents with citation tracking."""
    try:
        conv, user_msg, asst_msg, citations = await rag_service.answer_question(
            db=db,
            user_id=current_user.id,
            question=payload.question,
            conversation_id=payload.conversation_id,
            document_id=payload.document_id,
            collection_id=payload.collection_id,
        )
    except ValueError as ve:
        err_msg = str(ve)
        logger.warning(f"Validation failure in RAG inquiry: {err_msg}")
        if "not found or access denied" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except RuntimeError as re:
        err_msg = str(re)
        logger.error(f"Runtime error in RAG pipeline: {err_msg}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=err_msg,
        )
    except Exception as e:
        logger.exception("Unexpected error in RAG pipeline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the document research response.",
        )

    return AskQuestionResponse(
        conversation_id=conv.id,
        user_message=MessageResponse(
            id=user_msg.id,
            conversation_id=user_msg.conversation_id,
            role=user_msg.role,
            content=user_msg.content,
            created_at=user_msg.created_at,
            citations=[],
        ),
        assistant_message=MessageResponse(
            id=asst_msg.id,
            conversation_id=asst_msg.conversation_id,
            role=asst_msg.role,
            content=asst_msg.content,
            created_at=asst_msg.created_at,
            citations=[
                CitationResponse(
                    id=c.id,
                    message_id=c.message_id,
                    document_id=c.document_id,
                    chunk_id=c.chunk_id,
                    document_name=c.document_name,
                    page_number=c.page_number,
                    snippet=c.snippet,
                    relevance_score=c.relevance_score,
                    created_at=c.created_at,
                )
                for c in citations
            ],
        ),
    )
