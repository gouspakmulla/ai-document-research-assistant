import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, PrimaryKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.document import Document
    from backend.app.models.conversation import Conversation

class Collection(Base, TimestampMixin):
    __tablename__ = "collections"

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
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="collections")
    document_associations: Mapped[List["CollectionDocument"]] = relationship(
        "CollectionDocument",
        back_populates="collection",
        cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="collection"
    )

    __table_args__ = (
        Index("ix_collections_user_name", "user_id", "name"),
    )

class CollectionDocument(Base):
    __tablename__ = "collection_documents"

    collection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    collection: Mapped["Collection"] = relationship("Collection", back_populates="document_associations")
    document: Mapped["Document"] = relationship("Document", back_populates="collection_associations")

    __table_args__ = (
        PrimaryKeyConstraint("collection_id", "document_id"),
        Index("ix_colldoc_document_id", "document_id"),
    )
