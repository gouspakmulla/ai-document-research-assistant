import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin

# Import pgvector type
try:
    from pgvector.sqlalchemy import Vector
    VectorType = Vector(1536)
except ImportError:
    from sqlalchemy import JSON
    VectorType = JSON

if TYPE_CHECKING:
    from backend.app.models.document import Document
    from backend.app.models.user import User

class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    embedding = mapped_column(
        VectorType,
        nullable=True
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_user_doc_page", "user_id", "document_id", "page_number"),
    )
