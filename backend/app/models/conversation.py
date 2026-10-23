import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.collection import Collection
    from backend.app.models.citation import MessageCitation

class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

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
    title: Mapped[str] = mapped_column(
        String(255),
        default="New Research Inquiry",
        nullable=False
    )
    collection_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    collection: Mapped["Collection | None"] = relationship("Collection", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False  # user, assistant, system
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    citations: Mapped[List["MessageCitation"]] = relationship(
        "MessageCitation",
        back_populates="message",
        cascade="all, delete-orphan"
    )
