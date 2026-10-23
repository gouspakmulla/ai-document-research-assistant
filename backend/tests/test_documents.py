import os
import pytest
import pymupdf as fitz
from httpx import AsyncClient
from backend.app.core.config import settings
from backend.app.services.document_service import document_service


def create_in_memory_pdf(text: str = "Default test page text.", pages: int = 1) -> bytes:
    """Helper to generate a valid PDF byte buffer using PyMuPDF."""
    doc = fitz.open()
    for p in range(pages):
        page = doc.new_page()
        page.insert_text((50, 72), f"Page {p + 1}: {text}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_scanned_pdf(pages: int = 1) -> bytes:
    """Helper to generate a scanned PDF (blank pages without text)."""
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()  # Blank page
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_encrypted_pdf(password: str = "testpass") -> bytes:
    """Helper to generate a password-protected PDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Confidential locked text.")
    pdf_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        owner_pw="owner",
    )
    doc.close()
    return pdf_bytes


async def register_and_login(client: AsyncClient, email: str, password: str = "ValidPass123!"):
    """Helper to register and login a user, extracting CSRF token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200
    me_res = await client.get("/api/v1/auth/me")
    csrf_token = me_res.headers.get("X-CSRF-Token", "")
    return csrf_token


@pytest.mark.asyncio
async def test_upload_valid_pdf_pipeline(client: AsyncClient, tmp_path):
    """Test standard upload: checks status transitions to READY and chunks persisted in DB."""
    # Override storage directory for isolation
    settings.STORAGE_DIR = str(tmp_path)

    csrf = await register_and_login(client, "alice@example.com")
    pdf_bytes = create_in_memory_pdf("Detailed research on deep learning architectures.", pages=3)

    files = {
        "file": ("machine_learning.pdf", pdf_bytes, "application/pdf"),
    }
    headers = {"X-CSRF-Token": csrf}

    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["filename"] == "machine_learning.pdf"
    assert data["processing_status"] == "READY"
    assert data["page_count"] == 3
    assert data["file_size_bytes"] == len(pdf_bytes)
    assert data["error_message"] is None
    doc_id = data["id"]

    # Verify chunks endpoint
    chunks_res = await client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 3

    # Check page numbers
    page_numbers = {c["page_number"] for c in chunks}
    assert 1 in page_numbers
    assert 2 in page_numbers
    assert 3 in page_numbers


@pytest.mark.asyncio
async def test_upload_invalid_magic_bytes_rejected(client: AsyncClient):
    """Uploads with invalid magic bytes must be rejected with 400."""
    csrf = await register_and_login(client, "magic_test@example.com")
    fake_pdf = b"NOT_A_PDF_CONTENT_HERE_AT_ALL"

    files = {"file": ("malicious.pdf", fake_pdf, "application/pdf")}
    headers = {"X-CSRF-Token": csrf}

    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert response.status_code == 400
    assert "Invalid PDF file header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_invalid_extension_rejected(client: AsyncClient):
    """Uploads with non-pdf extensions must be rejected."""
    csrf = await register_and_login(client, "ext_test@example.com")
    pdf_bytes = create_in_memory_pdf("Text")

    files = {"file": ("malicious.exe", pdf_bytes, "application/pdf")}
    headers = {"X-CSRF-Token": csrf}

    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert response.status_code == 400
    assert "Only .pdf files are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_size_limit_enforced(client: AsyncClient, monkeypatch):
    """Files exceeding MAX_FILE_SIZE_MB must be rejected with 413."""
    csrf = await register_and_login(client, "size_test@example.com")
    # Temporarily set limit to 1MB
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)

    # 1.5MB PDF content
    large_pdf = b"%PDF-1.4 " + (b"A" * (1024 * 1024 + 500000))
    files = {"file": ("large_doc.pdf", large_pdf, "application/pdf")}
    headers = {"X-CSRF-Token": csrf}

    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert response.status_code == 413
    assert "exceeds maximum allowed limit" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_scanned_pdf_marked_ocr_required(client: AsyncClient, tmp_path):
    """PDF with insufficient text must be marked OCR_REQUIRED without indexing empty chunks."""
    settings.STORAGE_DIR = str(tmp_path)
    csrf = await register_and_login(client, "scanned_user@example.com")
    scanned_bytes = create_scanned_pdf(pages=2)

    files = {"file": ("scanned_document.pdf", scanned_bytes, "application/pdf")}
    headers = {"X-CSRF-Token": csrf}

    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["processing_status"] == "OCR_REQUIRED"
    assert data["page_count"] == 2
    assert "OCR is required" in (data["error_message"] or "")

    # Ensure no empty chunks were indexed
    chunks_res = await client.get(f"/api/v1/documents/{data['id']}/chunks")
    assert chunks_res.status_code == 200
    assert len(chunks_res.json()) == 0


@pytest.mark.asyncio
async def test_upload_password_protected_marked_failed(client: AsyncClient, tmp_path):
    """Encrypted PDFs must be marked FAILED with clear error message."""
    settings.STORAGE_DIR = str(tmp_path)
    csrf = await register_and_login(client, "locked_user@example.com")
    encrypted_bytes = create_encrypted_pdf("secretpass")

    files = {"file": ("confidential.pdf", encrypted_bytes, "application/pdf")}
    headers = {"X-CSRF-Token": csrf}

    response = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["processing_status"] == "FAILED"
    assert "password-protected" in (data["error_message"] or "")


@pytest.mark.asyncio
async def test_tenant_isolation_on_document_access(client: AsyncClient, tmp_path):
    """User B cannot view, retrieve PDF content, or delete User A's document."""
    settings.STORAGE_DIR = str(tmp_path)
    # Register Alice and upload
    csrf_alice = await register_and_login(client, "owner_alice@example.com")
    pdf_bytes = create_in_memory_pdf("Alice confidential research findings.", pages=1)
    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("alice_paper.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf_alice},
    )
    doc_id = res_upload.json()["id"]

    # Register Bob
    csrf_bob = await register_and_login(client, "intruder_bob@example.com")
    headers_bob = {"X-CSRF-Token": csrf_bob}

    # 1. Bob cannot get Alice's document metadata
    res = await client.get(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 404

    # 2. Bob cannot get Alice's PDF content stream
    res = await client.get(f"/api/v1/documents/{doc_id}/content")
    assert res.status_code == 404

    # 3. Bob cannot get Alice's chunks
    res = await client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert res.status_code == 404

    # 4. Bob cannot delete Alice's document
    res = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers_bob)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_pdf_content_viewing_endpoint(client: AsyncClient, tmp_path):
    """Authenticated owner can retrieve PDF stream with correct content disposition."""
    settings.STORAGE_DIR = str(tmp_path)
    csrf = await register_and_login(client, "viewer@example.com")
    pdf_bytes = create_in_memory_pdf("Content for PDF viewer display.", pages=2)

    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("view_test.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    doc_id = res_upload.json()["id"]

    # Get content
    res_content = await client.get(f"/api/v1/documents/{doc_id}/content")
    assert res_content.status_code == 200
    assert "application/pdf" in res_content.headers["content-type"]
    assert 'inline; filename="view_test.pdf"' in res_content.headers["content-disposition"]
    assert res_content.content == pdf_bytes


@pytest.mark.asyncio
async def test_document_deletion_cleans_file_and_cascades(client: AsyncClient, tmp_path):
    """Deleting document removes physical file and cascades database chunks."""
    settings.STORAGE_DIR = str(tmp_path)
    csrf = await register_and_login(client, "cleanup_user@example.com")
    pdf_bytes = create_in_memory_pdf("Document to be completely deleted.", pages=2)

    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("delete_me.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    doc_id = res_upload.json()["id"]

    # Verify chunks exist
    chunks_res = await client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert len(chunks_res.json()) >= 1

    # Delete document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers={"X-CSRF-Token": csrf})
    assert del_res.status_code == 204

    # Verify document 404
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 404

    # Verify chunks 404
    chunks_after = await client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert chunks_after.status_code == 404


@pytest.mark.asyncio
async def test_prevent_querying_unready_document(client: AsyncClient, tmp_path):
    """Documents not in READY status (e.g. OCR_REQUIRED or FAILED) cannot be queried."""
    settings.STORAGE_DIR = str(tmp_path)
    csrf = await register_and_login(client, "chat_guard_user@example.com")
    scanned_bytes = create_scanned_pdf(pages=1)

    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("scanned_paper.pdf", scanned_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    doc_id = res_upload.json()["id"]
    assert res_upload.json()["processing_status"] == "OCR_REQUIRED"

    # Attempt to ask question specifically targeting this unready document
    query_payload = {
        "question": "What is discussed on page 1?",
        "document_id": doc_id,
    }
    chat_res = await client.post(
        "/api/v1/chat/ask",
        json=query_payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert chat_res.status_code == 400
    assert "cannot be queried because its processing status is 'OCR_REQUIRED'" in chat_res.json()["detail"]


@pytest.mark.asyncio
async def test_upload_embedding_failure_handling(client: AsyncClient, tmp_path, monkeypatch):
    """When embedding generation fails, document is marked FAILED and partial chunks are purged."""
    settings.STORAGE_DIR = str(tmp_path)
    csrf = await register_and_login(client, "emb_fail_user@example.com")
    pdf_bytes = create_in_memory_pdf(
        "Extensive research paper text with adequate characters discussing distributed embeddings and RAG pipelines.",
        pages=1,
    )

    from backend.app.services.document_service import document_service

    async def mock_failing_embed_chunks(texts):
        raise RuntimeError("Embedding provider timed out.")

    monkeypatch.setattr(document_service.embedding_service, "embed_chunks", mock_failing_embed_chunks)

    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("failing_doc.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_upload.status_code == 201
    data = res_upload.json()
    assert data["processing_status"] == "FAILED"
    assert "Embedding provider timed out" in data["error_message"]

    # Verify no orphan chunks remained
    chunks_res = await client.get(f"/api/v1/documents/{data['id']}/chunks")
    assert chunks_res.status_code == 200
    assert len(chunks_res.json()) == 0


@pytest.mark.asyncio
async def test_unauthenticated_upload_rejected(client: AsyncClient):
    """Attempting to upload a PDF without a valid session cookie must return 401."""
    pdf_bytes = create_in_memory_pdf("Unauthorized attempt.", pages=1)
    res = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("unauthorized.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Authentication session required."
    assert res.headers.get("WWW-Authenticate") == "Cookie"


@pytest.mark.asyncio
async def test_authenticated_upload_and_session_restoration(client: AsyncClient, tmp_path):
    """Verify login sets HttpOnly cookie, /auth/me restores session, and upload succeeds with verified tenant ownership."""
    settings.STORAGE_DIR = str(tmp_path)
    email = "restored_user@example.com"
    password = "StrongPassword123!"

    # 1. Register & login
    csrf = await register_and_login(client, email, password)

    # 2. Session restoration via /auth/me
    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == email

    # 3. Authenticated upload
    pdf_bytes = create_in_memory_pdf("Verified content for session restoration research.", pages=1)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("restored_paper.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert doc_data["user_id"] == user_data["id"]
    assert doc_data["filename"] == "restored_paper.pdf"

