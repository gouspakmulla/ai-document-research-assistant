import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.collection import Collection, CollectionDocument
from backend.app.services.embedding_service import embedding_service
from backend.app.services.retrieval_service import retrieval_service


async def create_user(db: AsyncSession, email: str) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password="hashed_password",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_document(
    db: AsyncSession,
    user_id: str,
    filename: str,
    status: str = "READY",
) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=user_id,
        filename=filename,
        storage_path=f"/dummy/{filename}",
        file_size_bytes=1024,
        mime_type="application/pdf",
        page_count=5,
        processing_status=status,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def create_chunk(
    db: AsyncSession,
    doc: Document,
    page_number: int,
    chunk_index: int,
    content: str,
) -> DocumentChunk:
    emb = await embedding_service.embed_query(content)
    chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        user_id=doc.user_id,
        chunk_index=chunk_index,
        page_number=page_number,
        content=content,
        token_count=len(content.split()),
        embedding=emb,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    return chunk


@pytest.mark.asyncio
async def test_semantic_ranking_and_top_k(test_db_session: AsyncSession):
    """Retrieval service must rank results by cosine similarity and respect top_k."""
    db = test_db_session
    user = await create_user(db, "researcher1@example.com")
    doc = await create_document(db, user.id, "neural_networks.pdf")

    # Seed chunks with varying relevance to "attention mechanisms in transformer networks"
    high_rel = await create_chunk(
        db, doc, 1, 0, "Self-attention mechanisms in transformer networks allow dynamic contextual weighting."
    )
    med_rel = await create_chunk(
        db, doc, 2, 1, "Transformer models and neural networks utilize gradient descent optimization."
    )
    low_rel = await create_chunk(
        db, doc, 3, 2, "Geological formations and mineral classification in the jurassic basin."
    )

    results = await retrieval_service.search(
        db=db,
        user_id=user.id,
        query="transformer self-attention mechanism",
        top_k=2,
        similarity_threshold=0.1,
    )

    assert len(results) == 2
    assert results[0].chunk_id == high_rel.id
    assert results[0].page_number == 1
    assert results[0].relevance_score > results[1].relevance_score
    # Low relevance result should not be in top 2
    chunk_ids = [r.chunk_id for r in results]
    assert low_rel.id not in chunk_ids


@pytest.mark.asyncio
async def test_similarity_threshold_filtering(test_db_session: AsyncSession):
    """Chunks below similarity_threshold must be filtered out."""
    db = test_db_session
    user = await create_user(db, "threshold_user@example.com")
    doc = await create_document(db, user.id, "quantum_computing.pdf")

    await create_chunk(
        db, doc, 1, 0, "Quantum computing error correction codes and fault-tolerant stabilizer circuits."
    )
    await create_chunk(
        db, doc, 2, 1, "The biological lifecycle of amphibians in freshwater marshlands."
    )

    # Query quantum with high threshold (e.g. 0.6)
    results = await retrieval_service.search(
        db=db,
        user_id=user.id,
        query="quantum computing error correction circuits",
        similarity_threshold=0.6,
    )

    assert len(results) == 1
    assert "quantum" in results[0].snippet.lower()
    assert results[0].relevance_score >= 0.6


@pytest.mark.asyncio
async def test_retrieval_tenant_isolation(test_db_session: AsyncSession):
    """User B must never retrieve User A's chunks regardless of vector similarity."""
    db = test_db_session
    alice = await create_user(db, "alice_isolated@example.com")
    bob = await create_user(db, "bob_isolated@example.com")

    doc_alice = await create_document(db, alice.id, "alice_confidential.pdf")
    doc_bob = await create_document(db, bob.id, "bob_public.pdf")

    # Alice has the exact matching excerpt
    query_text = "Highly proprietary patent algorithms for synthetic fuel production"
    await create_chunk(db, doc_alice, 1, 0, query_text)
    await create_chunk(db, doc_bob, 1, 0, "General chemistry overview.")

    # Bob searches for the exact text of Alice's confidential paper
    bob_results = await retrieval_service.search(
        db=db,
        user_id=bob.id,
        query=query_text,
        similarity_threshold=0.1,
    )

    for r in bob_results:
        assert r.document_id != doc_alice.id
        assert query_text not in r.snippet


@pytest.mark.asyncio
async def test_scoping_by_document_and_collection(test_db_session: AsyncSession):
    """Search correctly filters by document_id or collection_id."""
    db = test_db_session
    user = await create_user(db, "collection_user@example.com")

    doc1 = await create_document(db, user.id, "doc1.pdf")
    doc2 = await create_document(db, user.id, "doc2.pdf")

    # Collection containing only doc1
    col = Collection(id=str(uuid.uuid4()), user_id=user.id, name="AI Research")
    db.add(col)
    await db.commit()

    link = CollectionDocument(collection_id=col.id, document_id=doc1.id)
    db.add(link)
    await db.commit()

    await create_chunk(db, doc1, 1, 0, "Artificial intelligence research in natural language processing.")
    await create_chunk(db, doc2, 1, 0, "Artificial intelligence research in computer vision graphics.")

    # 1. Scoped to doc1 specifically
    res_doc1 = await retrieval_service.search(
        db=db,
        user_id=user.id,
        query="artificial intelligence research",
        document_id=doc1.id,
    )
    assert len(res_doc1) == 1
    assert res_doc1[0].document_id == doc1.id

    # 2. Scoped to collection (which only has doc1)
    res_col = await retrieval_service.search(
        db=db,
        user_id=user.id,
        query="artificial intelligence research",
        collection_id=col.id,
    )
    assert len(res_col) == 1
    assert res_col[0].document_id == doc1.id


@pytest.mark.asyncio
async def test_unready_documents_excluded_from_retrieval(test_db_session: AsyncSession):
    """Chunks from documents with status != READY are omitted from search results."""
    db = test_db_session
    user = await create_user(db, "unready_user@example.com")

    # Create unready documents
    doc_failed = await create_document(db, user.id, "failed.pdf", status="FAILED")
    doc_ocr = await create_document(db, user.id, "ocr.pdf", status="OCR_REQUIRED")
    doc_ready = await create_document(db, user.id, "ready.pdf", status="READY")

    query = "Statistical mechanics and thermodynamics"
    await create_chunk(db, doc_failed, 1, 0, query)
    await create_chunk(db, doc_ocr, 1, 0, query)
    await create_chunk(db, doc_ready, 1, 0, query)

    results = await retrieval_service.search(
        db=db,
        user_id=user.id,
        query=query,
        similarity_threshold=0.5,
    )

    assert len(results) == 1
    assert results[0].document_id == doc_ready.id


@pytest.mark.asyncio
async def test_search_api_route_integration(client: AsyncClient, test_db_session: AsyncSession):
    """Integration test for POST /api/v1/search endpoint with CSRF and auth."""
    # Register & login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "api_searcher@example.com", "password": "SearchPassword123!"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "api_searcher@example.com", "password": "SearchPassword123!"},
    )
    me_res = await client.get("/api/v1/auth/me")
    csrf = me_res.headers.get("X-CSRF-Token", "")
    user_id = me_res.json()["id"]

    # Seed document & chunk for user
    doc = await create_document(test_db_session, user_id, "api_paper.pdf")
    await create_chunk(
        test_db_session,
        doc,
        page_number=3,
        chunk_index=0,
        content="Reinforcement learning from human feedback aligns language models effectively.",
    )

    # Execute search via API
    payload = {
        "query": "reinforcement learning human feedback",
        "top_k": 5,
        "similarity_threshold": 0.5,
    }
    headers = {"X-CSRF-Token": csrf}
    response = await client.post("/api/v1/search", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == payload["query"]
    assert data["total_results"] == 1
    assert data["results"][0]["page_number"] == 3
    assert data["results"][0]["filename"] == "api_paper.pdf"
    assert data["results"][0]["relevance_score"] >= 0.5
