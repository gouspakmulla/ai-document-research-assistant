import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.conversation import Message
    from backend.app.models.document import Document
    from backend.app.models.chunk import DocumentChunk

class MessageCitation(Base, TimestampMixin):
    __tablename__ = "message_citations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    document_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    snippet: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    relevance_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="citations")

    __table_args__ = (
        Index("ix_citations_doc_page", "document_id", "page_number"),
    )
