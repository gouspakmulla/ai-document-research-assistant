"""perf and security fixes (RLS, covering FK indexes, deduplicate indexes)

Revision ID: 003_perf_security
Revises: 002_vector_hnsw_index
Create Date: 2026-10-24 21:08:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_perf_security"
down_revision: Union[str, None] = "002_vector_hnsw_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1. Drop redundant duplicate index on users(email), keeping users_email_key
    if dialect == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email;"))
    else:
        try:
            op.drop_index("ix_users_email", table_name="users")
        except Exception:
            pass

    # 2. Covering index for conversations.collection_id foreign key
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_conversations_collection_id "
                "ON conversations (collection_id);"
            )
        )
    else:
        try:
            op.create_index("ix_conversations_collection_id", "conversations", ["collection_id"])
        except Exception:
            pass

    # 3. Covering index for message_citations.chunk_id foreign key
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_message_citations_chunk_id "
                "ON message_citations (chunk_id);"
            )
        )
    else:
        try:
            op.create_index("ix_message_citations_chunk_id", "message_citations", ["chunk_id"])
        except Exception:
            pass

    # 4. Covering index for documents.checksum_sha256
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_documents_checksum_sha256 "
                "ON documents (checksum_sha256);"
            )
        )
    else:
        try:
            op.create_index("ix_documents_checksum_sha256", "documents", ["checksum_sha256"])
        except Exception:
            pass

    # 5. Enable Row Level Security (RLS) on all public tables in PostgreSQL
    if dialect == "postgresql":
        public_tables = [
            "alembic_version",
            "users",
            "documents",
            "document_chunks",
            "collections",
            "collection_documents",
            "conversations",
            "messages",
            "message_citations",
        ]
        for tbl in public_tables:
            op.execute(sa.text(f'ALTER TABLE "{tbl}" ENABLE ROW LEVEL SECURITY;'))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS ix_documents_checksum_sha256;"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_message_citations_chunk_id;"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_conversations_collection_id;"))
        op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);"))
    else:
        try:
            op.drop_index("ix_documents_checksum_sha256", table_name="documents")
            op.drop_index("ix_message_citations_chunk_id", table_name="message_citations")
            op.drop_index("ix_conversations_collection_id", table_name="conversations")
            op.create_index("ix_users_email", "users", ["email"], unique=True)
        except Exception:
            pass
