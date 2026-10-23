import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, BigInteger, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.chunk import DocumentChunk
    from backend.app.models.collection import CollectionDocument

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        default="application/pdf",
        nullable=False
    )
    page_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    collection_associations: Mapped[List["CollectionDocument"]] = relationship(
        "CollectionDocument",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_user_id_created_at", "user_id", "created_at"),
    )
