import math
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.collection import Collection, CollectionDocument
from backend.app.services.embedding_service import embedding_service, EmbeddingService


@dataclass
class SearchResult:
    """Structured semantic search result."""
    document_id: str
    filename: str
    chunk_id: str
    page_number: int
    snippet: str
    relevance_score: float


def compute_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))


class RetrievalService:
    """Service for semantic similarity search over document chunks using pgvector."""

    def __init__(self, emb_service: EmbeddingService = embedding_service):
        self.embedding_service = emb_service

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        document_id: Optional[str] = None,
        collection_id: Optional[str] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """Search user chunks matching query vector, filtered by user_id and optional scopes."""
        k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
        default_threshold = (
            0.25
            if settings.EMBEDDING_PROVIDER == "mock"
            else settings.RETRIEVAL_SIMILARITY_THRESHOLD
        )
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else default_threshold
        )


        # 1. Embed query text
        query_vec = await self.embedding_service.embed_query(query)

        # Detect dialect: PostgreSQL with pgvector vs SQLite fallback (testing)
        bind = db.bind
        dialect_name = bind.dialect.name if bind else "sqlite"

        if dialect_name == "postgresql":
            return await self._search_postgres_pgvector(
                db=db,
                user_id=user_id,
                query_vec=query_vec,
                document_id=document_id,
                collection_id=collection_id,
                top_k=k,
                similarity_threshold=threshold,
            )
        else:
            return await self._search_in_memory_fallback(
                db=db,
                user_id=user_id,
                query_vec=query_vec,
                document_id=document_id,
                collection_id=collection_id,
                top_k=k,
                similarity_threshold=threshold,
            )

    async def _search_postgres_pgvector(
        self,
        db: AsyncSession,
        user_id: str,
        query_vec: List[float],
        document_id: Optional[str],
        collection_id: Optional[str],
        top_k: int,
        similarity_threshold: float,
    ) -> List[SearchResult]:
        """Execute pgvector HNSW cosine similarity search on PostgreSQL."""
        cosine_distance = DocumentChunk.embedding.cosine_distance(query_vec)
        similarity = (1.0 - cosine_distance).label("relevance_score")

        stmt = (
            select(
                DocumentChunk.id.label("chunk_id"),
                DocumentChunk.document_id,
                DocumentChunk.page_number,
                DocumentChunk.content.label("snippet"),
                Document.filename,
                similarity,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.user_id == user_id,
                Document.user_id == user_id,
                Document.processing_status == "READY",
            )
        )

        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        if collection_id:
            stmt = stmt.where(
                DocumentChunk.document_id.in_(
                    select(CollectionDocument.document_id)
                    .join(Collection, Collection.id == CollectionDocument.collection_id)
                    .where(
                        CollectionDocument.collection_id == collection_id,
                        Collection.user_id == user_id,
                    )
                )
            )

        stmt = (
            stmt.where(similarity >= similarity_threshold)
            .order_by(cosine_distance.asc())
            .limit(top_k)
        )

        result = await db.execute(stmt)
        rows = result.all()

        return [
            SearchResult(
                document_id=row.document_id,
                filename=row.filename,
                chunk_id=row.chunk_id,
                page_number=row.page_number,
                snippet=row.snippet,
                relevance_score=float(row.relevance_score),
            )
            for row in rows
        ]

    async def _search_in_memory_fallback(
        self,
        db: AsyncSession,
        user_id: str,
        query_vec: List[float],
        document_id: Optional[str],
        collection_id: Optional[str],
        top_k: int,
        similarity_threshold: float,
    ) -> List[SearchResult]:
        """Fallback evaluation for SQLite / offline test environments."""
        stmt = (
            select(
                DocumentChunk.id.label("chunk_id"),
                DocumentChunk.document_id,
                DocumentChunk.page_number,
                DocumentChunk.content.label("snippet"),
                DocumentChunk.embedding,
                Document.filename,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.user_id == user_id,
                Document.user_id == user_id,
                Document.processing_status == "READY",
            )
        )

        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        if collection_id:
            stmt = stmt.where(
                DocumentChunk.document_id.in_(
                    select(CollectionDocument.document_id)
                    .join(Collection, Collection.id == CollectionDocument.collection_id)
                    .where(
                        CollectionDocument.collection_id == collection_id,
                        Collection.user_id == user_id,
                    )
                )
            )

        result = await db.execute(stmt)
        rows = result.all()

        scored: List[SearchResult] = []
        for r in rows:
            emb = r.embedding
            if emb is not None:
                score = compute_cosine_similarity(query_vec, emb)
                if score >= similarity_threshold:
                    scored.append(
                        SearchResult(
                            document_id=r.document_id,
                            filename=r.filename,
                            chunk_id=r.chunk_id,
                            page_number=r.page_number,
                            snippet=r.snippet,
                            relevance_score=round(score, 4),
                        )
                    )

        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored[:top_k]


retrieval_service = RetrievalService()
