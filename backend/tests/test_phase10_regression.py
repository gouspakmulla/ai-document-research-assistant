import io
import pytest
import pymupdf as fitz
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.conversation import Conversation, Message
from backend.app.models.citation import MessageCitation
from backend.app.services.rag_service import INSUFFICIENT_EVIDENCE_ANSWER


def make_pdf(page_texts: list[str]) -> bytes:
    """Generate in-memory PDF with specified text per page."""
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def auth_user(client: AsyncClient, email: str, name: str = "Test User") -> str:
    """Register and login user, returning CSRF token."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePassword123!",
        "full_name": name,
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePassword123!",
    })
    assert login_res.status_code == 200
    me_res = await client.get("/api/v1/auth/me")
    return me_res.headers.get("X-CSRF-Token", "")


@pytest.mark.asyncio
async def test_e2e_pdf_upload_chunking_embeddings_ready(client: AsyncClient, test_db_session: AsyncSession):
    """Verify PDF upload, extraction, chunk creation, embedding generation, and READY status."""
    csrf = await auth_user(client, "uploader@research.org", "PDF Ingestion Tester")

    pdf_content = make_pdf([
        "Introduction: Renewable energy sources replenish naturally on human timescales.",
        "Core Types: Three prominent examples of renewable energy are solar photovoltaic power, wind turbine energy, and hydroelectric power generation.",
        "Conclusion: Clean renewable technologies significantly reduce carbon emissions worldwide.",
    ])

    files = {"file": ("renewable_energy_guide.pdf", io.BytesIO(pdf_content), "application/pdf")}
    res = await client.post("/api/v1/documents/upload", files=files, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 201
    doc_data = res.json()

    assert doc_data["filename"] == "renewable_energy_guide.pdf"
    assert doc_data["processing_status"] == "READY"
    assert doc_data["page_count"] == 3
    doc_id = doc_data["id"]

    # Verify DB records
    db_doc_res = await test_db_session.execute(select(Document).where(Document.id == doc_id))
    db_doc = db_doc_res.scalars().first()
    assert db_doc is not None
    assert db_doc.processing_status == "READY"

    # Verify chunk creation and embeddings
    chunks_res = await test_db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
    chunks = chunks_res.scalars().all()
    assert len(chunks) >= 3
    for c in chunks:
        assert c.page_number in (1, 2, 3)
        assert c.token_count > 0
        assert c.embedding is not None
        assert len(c.content.strip()) > 0


@pytest.mark.asyncio
async def test_renewable_energy_query_grounded_citation(client: AsyncClient, test_db_session: AsyncSession):
    """Verify inquiry 'What are three examples of renewable energy?' retrieves and cites only the renewable doc,
    never citing the unrelated transformer paper.
    """
    csrf = await auth_user(client, "energy_researcher@lab.org", "Renewable Scientist")

    # 1. Upload renewable energy guide
    pdf_renewable = make_pdf([
        "Overview: Sustainable energy development.",
        "Three prominent examples of renewable energy are solar photovoltaic energy, wind turbine generation, and hydroelectric water power.",
    ])
    files_ren = {"file": ("renewable_energy_handbook.pdf", io.BytesIO(pdf_renewable), "application/pdf")}
    ren_res = await client.post("/api/v1/documents/upload", files=files_ren, headers={"X-CSRF-Token": csrf})
    assert ren_res.status_code == 201
    ren_doc_id = ren_res.json()["id"]

    # 2. Upload unrelated transformer research paper for same user
    pdf_trans = make_pdf([
        "We introduce the Transformer, a sequence transduction model relying entirely on self-attention mechanisms without recurrent layers.",
        "Multi-head attention mechanisms replace traditional recurrent and convolutional layers in neural networks.",
    ])
    files_trans = {"file": ("Attention_Is_All_You_Need_Transformer_Paper.pdf", io.BytesIO(pdf_trans), "application/pdf")}
    trans_res = await client.post("/api/v1/documents/upload", files=files_trans, headers={"X-CSRF-Token": csrf})
    assert trans_res.status_code == 201
    trans_doc_id = trans_res.json()["id"]

    # 3. Ask question
    ask_res = await client.post("/api/v1/chat/ask", json={
        "question": "What are three examples of renewable energy?",
    }, headers={"X-CSRF-Token": csrf})
    assert ask_res.status_code == 200
    data = ask_res.json()

    asst_msg = data["assistant_message"]
    citations = asst_msg["citations"]

    # Must contain citations
    assert len(citations) >= 1

    # Every citation must point strictly to renewable_energy_handbook.pdf
    for cit in citations:
        assert cit["document_id"] == ren_doc_id
        assert cit["document_name"] == "renewable_energy_handbook.pdf"
        assert cit["page_number"] in (1, 2)
        assert cit["document_id"] != trans_doc_id
        assert cit["document_name"] != "Attention_Is_All_You_Need_Transformer_Paper.pdf"

    # Answer content check
    content = asst_msg["content"]
    assert "renewable_energy_handbook.pdf" in content
    assert "Attention_Is_All_You_Need" not in content


@pytest.mark.asyncio
async def test_insufficient_evidence_produces_zero_citations(client: AsyncClient, test_db_session: AsyncSession):
    """Verify that an inquiry without supporting evidence returns honest insufficient-evidence response and 0 citations."""
    csrf = await auth_user(client, "quantum_skeptic@math.edu", "Researcher")

    pdf_ren = make_pdf([
        "Geothermal heat and ocean waves are alternative clean power generation methods.",
    ])
    files = {"file": ("geothermal_energy.pdf", io.BytesIO(pdf_ren), "application/pdf")}
    await client.post("/api/v1/documents/upload", files=files, headers={"X-CSRF-Token": csrf})

    # Ask completely unrelated query
    ask_res = await client.post("/api/v1/chat/ask", json={
        "question": "What are the rules of Byzantine fault tolerant distributed consensus algorithms?",
    }, headers={"X-CSRF-Token": csrf})
    assert ask_res.status_code == 200
    data = ask_res.json()

    asst_msg = data["assistant_message"]
    assert INSUFFICIENT_EVIDENCE_ANSWER in asst_msg["content"]
    assert len(asst_msg["citations"]) == 0


@pytest.mark.asyncio
async def test_retrieval_and_scoping_enforcement(client: AsyncClient, test_db_session: AsyncSession):
    """Verify document scoping strictly limits retrieval and blocks cross-collection/unowned docs."""
    csrf = await auth_user(client, "scoper@lab.gov", "Scoping Tester")

    # Doc A: Renewable
    pdf_a = make_pdf(["Solar panels convert sunlight directly into electricity."])
    doc_a = (await client.post("/api/v1/documents/upload", files={"file": ("solar.pdf", io.BytesIO(pdf_a), "application/pdf")}, headers={"X-CSRF-Token": csrf})).json()

    # Doc B: Quantum
    pdf_b = make_pdf(["Qubits can exist in coherent superpositions of basis states."])
    doc_b = (await client.post("/api/v1/documents/upload", files={"file": ("quantum.pdf", io.BytesIO(pdf_b), "application/pdf")}, headers={"X-CSRF-Token": csrf})).json()

    # Query scoped to solar.pdf
    ask_solar = await client.post("/api/v1/chat/ask", json={
        "question": "How do solar panels work?",
        "document_id": doc_a["id"],
    }, headers={"X-CSRF-Token": csrf})
    assert ask_solar.status_code == 200
    cits_solar = ask_solar.json()["assistant_message"]["citations"]
    assert len(cits_solar) >= 1
    assert all(c["document_id"] == doc_a["id"] for c in cits_solar)

    # Querying solar while scoped to quantum.pdf -> insufficient evidence
    ask_mismatch = await client.post("/api/v1/chat/ask", json={
        "question": "How do solar panels work?",
        "document_id": doc_b["id"],
    }, headers={"X-CSRF-Token": csrf})
    assert ask_mismatch.status_code == 200
    assert INSUFFICIENT_EVIDENCE_ANSWER in ask_mismatch.json()["assistant_message"]["content"]
    assert len(ask_mismatch.json()["assistant_message"]["citations"]) == 0

    # Scoping to non-existent or unowned document -> 404
    ask_fake = await client.post("/api/v1/chat/ask", json={
        "question": "How do solar panels work?",
        "document_id": "00000000-0000-0000-0000-000000000000",
    }, headers={"X-CSRF-Token": csrf})
    assert ask_fake.status_code == 404


@pytest.mark.asyncio
async def test_authentication_required_gates(client: AsyncClient):
    """Verify that unauthenticated requests to protected endpoints return 401."""
    pdf = make_pdf(["Unauthorized test file."])

    # Unauthenticated upload
    up_res = await client.post("/api/v1/documents/upload", files={"file": ("unauth.pdf", io.BytesIO(pdf), "application/pdf")})
    assert up_res.status_code == 401

    # Unauthenticated ask
    ask_res = await client.post("/api/v1/chat/ask", json={"question": "Hello?"})
    assert ask_res.status_code == 401

    # Unauthenticated list conversations
    conv_res = await client.get("/api/v1/chat/conversations")
    assert conv_res.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_isolation_strict(client: AsyncClient, test_db_session: AsyncSession):
    """Verify User B cannot access User A documents, chunks, or conversations."""
    # Register User A and upload confidential doc
    csrf_a = await auth_user(client, "user_alpha@corp.internal", "User Alpha")
    pdf_a = make_pdf(["Confidential financial results of Project Titan."])
    doc_a = (await client.post("/api/v1/documents/upload", files={"file": ("project_titan.pdf", io.BytesIO(pdf_a), "application/pdf")}, headers={"X-CSRF-Token": csrf_a})).json()

    # User A asks a question
    ask_a = (await client.post("/api/v1/chat/ask", json={"question": "What is Project Titan?"}, headers={"X-CSRF-Token": csrf_a})).json()
    conv_id = ask_a["conversation_id"]

    # Register User B
    csrf_b = await auth_user(client, "user_beta@external.org", "User Beta")

    # User B lists documents -> should be empty
    docs_b = (await client.get("/api/v1/documents")).json()
    assert len(docs_b) == 0

    # User B cannot get User A's document content -> 404
    content_b = await client.get(f"/api/v1/documents/{doc_a['id']}/content")
    assert content_b.status_code == 404

    # User B cannot query User A's document -> 404
    scoped_b = await client.post("/api/v1/chat/ask", json={
        "question": "What is Project Titan?",
        "document_id": doc_a["id"],
    }, headers={"X-CSRF-Token": csrf_b})
    assert scoped_b.status_code == 404

    # User B cannot access User A's conversation -> 404
    conv_b = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert conv_b.status_code == 404


@pytest.mark.asyncio
async def test_storage_persistence_content_stream_and_cascade_delete(client: AsyncClient, test_db_session: AsyncSession):
    """Verify storage download content stream matches uploaded bytes, and delete cascades completely."""
    csrf = await auth_user(client, "persistence@storage.org", "Persistence Tester")

    original_pdf = make_pdf([
        "Persistent document page 1.",
        "Persistent document page 2.",
    ])
    up_res = await client.post("/api/v1/documents/upload", files={
        "file": ("persistent_doc.pdf", io.BytesIO(original_pdf), "application/pdf"),
    }, headers={"X-CSRF-Token": csrf})
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    # Ask question to create conversation and citation records
    await client.post("/api/v1/chat/ask", json={
        "question": "What is on persistent document page 1?",
        "document_id": doc_id,
    }, headers={"X-CSRF-Token": csrf})

    # Download content stream and verify byte-for-byte identity
    dl_res = await client.get(f"/api/v1/documents/{doc_id}/content")
    assert dl_res.status_code == 200
    assert dl_res.content == original_pdf
    assert dl_res.headers.get("content-type") == "application/pdf"

    # Delete document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers={"X-CSRF-Token": csrf})
    assert del_res.status_code == 204

    # Verify document is gone from DB
    doc_check = await test_db_session.execute(select(Document).where(Document.id == doc_id))
    assert doc_check.scalars().first() is None

    # Verify chunks cascaded
    chunk_check = await test_db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
    assert len(chunk_check.scalars().all()) == 0

    # Verify content endpoint now returns 404
    del_dl_res = await client.get(f"/api/v1/documents/{doc_id}/content")
    assert del_dl_res.status_code == 404
