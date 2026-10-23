import json
import os
import pytest
import pymupdf as fitz
import httpx
from httpx import AsyncClient
from backend.app.core.config import settings
from backend.app.services.storage_service import (
    LocalStorageProvider,
    SupabaseStorageProvider,
    MockStorageProvider,
    StorageService,
    storage_service,
    StorageError,
    StorageFileNotFoundError,
    StorageValidationError,
    StorageConfigurationError,
)
from backend.app.services.document_service import document_service


def create_test_pdf(text: str = "Persistent storage test document.", pages: int = 1) -> bytes:
    """Helper to generate a valid PDF byte buffer using PyMuPDF."""
    doc = fitz.open()
    for p in range(pages):
        page = doc.new_page()
        page.insert_text((50, 72), f"Page {p + 1}: {text}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def register_and_login(client: AsyncClient, email: str, password: str = "ValidPass123!"):
    """Helper to register and login a user, extracting CSRF token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Storage User"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200
    me_res = await client.get("/api/v1/auth/me")
    csrf_token = me_res.headers.get("X-CSRF-Token", "")
    return csrf_token


# ==============================================================================
# 1. LOCAL STORAGE PROVIDER UNIT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_local_storage_upload_download_delete(tmp_path):
    """Local storage provider persists, retrieves, checks existence, and deletes files."""
    provider = LocalStorageProvider(base_dir=str(tmp_path))
    content = b"%PDF-1.4 Local Storage Content Test Bytes"

    # 1. Upload
    stored_path = await provider.upload_file(
        destination_path="user_123/test_doc.pdf",
        content=content,
        content_type="application/pdf",
    )
    assert os.path.exists(stored_path)
    assert await provider.file_exists(stored_path) is True

    # 2. Download
    retrieved = await provider.download_file(stored_path)
    assert retrieved == content

    # Download by relative destination path
    retrieved_rel = await provider.download_file("user_123/test_doc.pdf")
    assert retrieved_rel == content

    # 3. Delete
    deleted = await provider.delete_file(stored_path)
    assert deleted is True
    assert not os.path.exists(stored_path)
    assert await provider.file_exists(stored_path) is False

    # Deleting again returns False
    assert await provider.delete_file(stored_path) is False


@pytest.mark.asyncio
async def test_local_storage_path_traversal_prevention(tmp_path):
    """Local storage provider must reject any path traversal attempts."""
    provider = LocalStorageProvider(base_dir=str(tmp_path))
    content = b"Evil content"

    # Attempt path traversal in upload
    with pytest.raises(StorageValidationError, match="Path traversal detected"):
        await provider.upload_file(
            destination_path="../evil.pdf",
            content=content,
        )

    with pytest.raises(StorageValidationError, match="Path traversal detected"):
        await provider.upload_file(
            destination_path="subfolder/../../evil.pdf",
            content=content,
        )


@pytest.mark.asyncio
async def test_local_storage_missing_file_raises_not_found(tmp_path):
    """Downloading a missing file must raise StorageFileNotFoundError."""
    provider = LocalStorageProvider(base_dir=str(tmp_path))
    with pytest.raises(StorageFileNotFoundError, match="Local storage file not found"):
        await provider.download_file("nonexistent_folder/missing.pdf")


# ==============================================================================
# 2. SUPABASE STORAGE PROVIDER UNIT TESTS (via MockTransport)
# ==============================================================================

@pytest.mark.asyncio
async def test_supabase_storage_missing_config_raises():
    """Initializing SupabaseStorageProvider without URL or key raises StorageConfigurationError."""
    with pytest.raises(StorageConfigurationError, match="requires both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"):
        SupabaseStorageProvider(supabase_url=None, service_role_key=None)


@pytest.mark.asyncio
async def test_supabase_storage_upload_success():
    """SupabaseStorageProvider uploads object with server-side authorization headers."""
    uploaded_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/storage/v1/object/documents/user_abc/doc_123.pdf" in str(request.url)
        assert request.headers.get("Authorization") == "Bearer fake_service_key"
        assert request.headers.get("apiKey") == "fake_service_key"
        assert request.headers.get("Content-Type") == "application/pdf"
        uploaded_payload["body"] = request.read()
        return httpx.Response(200, json={"Key": "documents/user_abc/doc_123.pdf", "Id": "obj-1"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://testproject.supabase.co",
        service_role_key="fake_service_key",
        bucket_name="documents",
        client=mock_client,
    )

    pdf_content = b"%PDF-1.4 Mock Supabase PDF Payload"
    uri = await provider.upload_file(
        destination_path="user_abc/doc_123.pdf",
        content=pdf_content,
        content_type="application/pdf",
    )

    assert uri == "supabase://documents/user_abc/doc_123.pdf"
    assert uploaded_payload["body"] == pdf_content


@pytest.mark.asyncio
async def test_supabase_storage_download_success():
    """SupabaseStorageProvider downloads object using authenticated private bucket endpoint."""
    pdf_content = b"%PDF-1.4 Downloaded Supabase PDF Content"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/storage/v1/object/authenticated/documents/user_abc/doc_123.pdf" in str(request.url)
        assert request.headers.get("Authorization") == "Bearer fake_service_key"
        return httpx.Response(200, content=pdf_content, headers={"Content-Type": "application/pdf"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://testproject.supabase.co",
        service_role_key="fake_service_key",
        bucket_name="documents",
        client=mock_client,
    )

    data = await provider.download_file("supabase://documents/user_abc/doc_123.pdf")
    assert data == pdf_content


@pytest.mark.asyncio
async def test_supabase_storage_download_404_raises_not_found():
    """SupabaseStorageProvider raises StorageFileNotFoundError when object is missing."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"statusCode": "404", "error": "Not Found", "message": "Object not found"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://testproject.supabase.co",
        service_role_key="fake_service_key",
        bucket_name="documents",
        client=mock_client,
    )

    with pytest.raises(StorageFileNotFoundError, match="not found in Supabase Storage"):
        await provider.download_file("supabase://documents/user_abc/missing.pdf")


@pytest.mark.asyncio
async def test_supabase_storage_delete_success():
    """SupabaseStorageProvider sends batch delete request with prefixes."""
    deleted_prefixes = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert "/storage/v1/object/documents" in str(request.url)
        body = json.loads(request.read().decode())
        deleted_prefixes.extend(body.get("prefixes", []))
        return httpx.Response(200, json=[{"name": "user_abc/doc_123.pdf"}])

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://testproject.supabase.co",
        service_role_key="fake_service_key",
        bucket_name="documents",
        client=mock_client,
    )

    result = await provider.delete_file("supabase://documents/user_abc/doc_123.pdf")
    assert result is True
    assert "user_abc/doc_123.pdf" in deleted_prefixes


@pytest.mark.asyncio
async def test_supabase_storage_upload_bucket_not_found_raises():
    """SupabaseStorageProvider upload raises descriptive error when bucket does not exist."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Bucket not found"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://testproject.supabase.co",
        service_role_key="fake_service_key",
        bucket_name="documents",
        client=mock_client,
    )

    with pytest.raises(StorageError, match="Ensure the private bucket exists"):
        await provider.upload_file("user_1/doc.pdf", b"%PDF-1.4 test")


@pytest.mark.asyncio
async def test_supabase_storage_auth_failure_raises():
    """SupabaseStorageProvider raises descriptive error when credentials are rejected."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://testproject.supabase.co",
        service_role_key="invalid_key",
        bucket_name="documents",
        client=mock_client,
    )

    with pytest.raises(StorageError, match="authentication failed"):
        await provider.upload_file("user_1/doc.pdf", b"%PDF-1.4 test")


# ==============================================================================
# 3. STORAGE SERVICE FACADE & BACKWARD COMPATIBILITY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_storage_service_safe_path_builder():
    """StorageService generates sanitized, tenant-isolated paths and rejects traversal."""
    service = StorageService()

    # Valid user ID
    path = service.build_safe_object_path("user-456-uuid")
    assert path.startswith("user-456-uuid/")
    assert path.endswith(".pdf")

    # Path traversal in user ID sanitized out
    path_traversal = service.build_safe_object_path("../../etc/passwd")
    assert not path_traversal.startswith("..")
    assert "etcpasswd/" in path_traversal

    # Empty user ID raises
    with pytest.raises(StorageValidationError, match="User ID is required"):
        service.build_safe_object_path("")


@pytest.mark.asyncio
async def test_storage_service_backwards_compatibility_local_file_retrieval(tmp_path, monkeypatch):
    """StorageService downloads existing local files even if STORAGE_BACKEND is set to supabase."""
    # 1. Create a local file
    local_dir = tmp_path / "legacy_docs"
    local_dir.mkdir()
    legacy_file = local_dir / "legacy_report.pdf"
    content = b"%PDF-1.4 Legacy Local Document Bytes"
    legacy_file.write_bytes(content)

    # 2. Configure environment as supabase with mock client
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(local_dir))

    # Mock supabase provider that would fail if called
    def fail_handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Supabase provider should not be called for existing local file path!")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(fail_handler))
    supa_provider = SupabaseStorageProvider(
        supabase_url="https://test.supabase.co",
        service_role_key="fake_key",
        client=mock_client,
    )

    service = StorageService(supabase_provider=supa_provider)

    # 3. Download using absolute local path -> retrieves local file
    retrieved = await service.download_file(str(legacy_file))
    assert retrieved == content

    # 4. Download using legacy basename -> retrieves local file
    retrieved_base = await service.download_file("legacy_report.pdf")
    assert retrieved_base == content


@pytest.mark.asyncio
async def test_mock_storage_provider():
    """MockStorageProvider performs in-memory storage without network or filesystem."""
    mock_p = MockStorageProvider()
    data = b"%PDF-1.4 In-Memory Mock Bytes"

    key = await mock_p.upload_file("user_x/file.pdf", data)
    assert key.startswith("mock://documents/user_x/file.pdf")
    assert await mock_p.file_exists(key) is True

    downloaded = await mock_p.download_file(key)
    assert downloaded == data

    assert await mock_p.delete_file(key) is True
    assert await mock_p.file_exists(key) is False

    with pytest.raises(StorageFileNotFoundError):
        await mock_p.download_file(key)


# ==============================================================================
# 4. INTEGRATION TESTS (API Endpoints + Document Processing Pipeline)
# ==============================================================================

@pytest.mark.asyncio
async def test_end_to_end_upload_and_download_with_supabase_storage(client: AsyncClient, monkeypatch):
    """End-to-end integration: PDF upload persists to Supabase Storage, extracts chunks, and streams content."""
    stored_objects = {}

    def supabase_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # Upload endpoint: POST /storage/v1/object/documents/{path}
        if request.method == "POST" and "/storage/v1/object/documents/" in url_str:
            path = url_str.split("/storage/v1/object/documents/")[1]
            stored_objects[path] = request.read()
            return httpx.Response(200, json={"Key": f"documents/{path}"})

        # Download endpoint: GET /storage/v1/object/authenticated/documents/{path}
        if request.method == "GET" and "/storage/v1/object/authenticated/documents/" in url_str:
            path = url_str.split("/storage/v1/object/authenticated/documents/")[1]
            if path in stored_objects:
                return httpx.Response(200, content=stored_objects[path], headers={"Content-Type": "application/pdf"})
            return httpx.Response(404, json={"message": "Not found"})

        # Delete endpoint: DELETE /storage/v1/object/documents
        if request.method == "DELETE" and "/storage/v1/object/documents" in url_str:
            body = json.loads(request.read().decode())
            for prefix in body.get("prefixes", []):
                stored_objects.pop(prefix, None)
            return httpx.Response(200, json=[{"name": p} for p in body.get("prefixes", [])])

        return httpx.Response(400, json={"detail": f"Unhandled mock route: {request.method} {url_str}"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(supabase_handler))
    supa_provider = SupabaseStorageProvider(
        supabase_url="https://mock-proj.supabase.co",
        service_role_key="mock_service_role_key_secret",
        bucket_name="documents",
        client=mock_client,
    )

    # Configure DocumentService to use this Supabase provider
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(document_service.storage_service, "_supabase_provider", supa_provider)

    csrf = await register_and_login(client, "supabase_user@example.com")
    pdf_bytes = create_test_pdf("Supabase cloud persistent storage integration research.", pages=2)

    files = {"file": ("cloud_paper.pdf", pdf_bytes, "application/pdf")}
    headers = {"X-CSRF-Token": csrf}

    # 1. Upload via API
    upload_res = await client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    doc_data = upload_res.json()

    assert doc_data["filename"] == "cloud_paper.pdf"
    assert doc_data["processing_status"] == "READY"
    assert doc_data["page_count"] == 2
    assert doc_data["file_size_bytes"] == len(pdf_bytes)

    doc_id = doc_data["id"]

    # Verify that the file was uploaded to Supabase Storage
    assert len(stored_objects) == 1
    stored_path = list(stored_objects.keys())[0]
    assert stored_objects[stored_path] == pdf_bytes

    # 2. Stream content via API
    content_res = await client.get(f"/api/v1/documents/{doc_id}/content")
    assert content_res.status_code == 200
    assert "application/pdf" in content_res.headers["content-type"]
    assert 'inline; filename="cloud_paper.pdf"' in content_res.headers["content-disposition"]
    assert content_res.content == pdf_bytes

    # 3. Chunks check
    chunks_res = await client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 2

    # 4. Delete document cleans up Supabase object and DB cascades
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers={"X-CSRF-Token": csrf})
    assert del_res.status_code == 204

    # Object should be purged from Supabase Storage
    assert len(stored_objects) == 0

    # Document should return 404
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_access_isolation_with_supabase_storage(client: AsyncClient, monkeypatch):
    """User B cannot access or stream User A's document persisted in Supabase Storage."""
    stored_objects = {}

    def supabase_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if request.method == "POST":
            path = url_str.split("/storage/v1/object/documents/")[1]
            stored_objects[path] = request.read()
            return httpx.Response(200, json={"Key": f"documents/{path}"})
        if request.method == "GET":
            path = url_str.split("/storage/v1/object/authenticated/documents/")[1]
            return httpx.Response(200, content=stored_objects[path])
        return httpx.Response(200)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(supabase_handler))
    supa_provider = SupabaseStorageProvider(
        supabase_url="https://isolation-proj.supabase.co",
        service_role_key="mock_key",
        client=mock_client,
    )
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(document_service.storage_service, "_supabase_provider", supa_provider)

    # Alice uploads
    csrf_alice = await register_and_login(client, "alice_storage@example.com")
    pdf_bytes = create_test_pdf("Alice private data.", pages=1)
    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("alice_secret.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf_alice},
    )
    alice_doc_id = res_upload.json()["id"]

    # Bob registers
    csrf_bob = await register_and_login(client, "bob_storage@example.com")

    # Bob attempts to access Alice's document content
    bob_content_res = await client.get(f"/api/v1/documents/{alice_doc_id}/content")
    assert bob_content_res.status_code == 404

    # Bob attempts to delete Alice's document
    bob_del_res = await client.delete(
        f"/api/v1/documents/{alice_doc_id}",
        headers={"X-CSRF-Token": csrf_bob},
    )
    assert bob_del_res.status_code == 404

    # Log Alice back in to verify her document is still intact
    await client.post(
        "/api/v1/auth/login",
        json={"email": "alice_storage@example.com", "password": "ValidPass123!"},
    )
    alice_content_res = await client.get(f"/api/v1/documents/{alice_doc_id}/content")
    assert alice_content_res.status_code == 200
    assert alice_content_res.content == pdf_bytes


@pytest.mark.asyncio
async def test_failed_storage_upload_leaves_no_orphan_db_record(client: AsyncClient, monkeypatch):
    """When storage upload fails, API returns error and does NOT leave an orphan DB record."""
    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "Internal Supabase Storage Error"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(failing_handler))
    supa_provider = SupabaseStorageProvider(
        supabase_url="https://fail-proj.supabase.co",
        service_role_key="mock_key",
        client=mock_client,
    )
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(document_service.storage_service, "_supabase_provider", supa_provider)

    csrf = await register_and_login(client, "storage_fail_user@example.com")
    pdf_bytes = create_test_pdf("Test bytes.")

    res = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("fail_doc.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 500
    assert "Storage upload failed" in res.json()["detail"]

    # Verify no documents exist in user library
    list_res = await client.get("/api/v1/documents")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0


@pytest.mark.asyncio
async def test_missing_storage_file_during_ingestion_marks_failed(client: AsyncClient, monkeypatch):
    """If the storage file disappears before pipeline extraction, document is marked FAILED."""
    def missing_on_download_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            # Upload succeeds
            return httpx.Response(200, json={"Key": "documents/mock/file.pdf"})
        if request.method == "GET":
            # Download returns 404
            return httpx.Response(404, json={"message": "Object not found"})
        return httpx.Response(200)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(missing_on_download_handler))
    supa_provider = SupabaseStorageProvider(
        supabase_url="https://missing-proj.supabase.co",
        service_role_key="mock_key",
        client=mock_client,
    )
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(document_service.storage_service, "_supabase_provider", supa_provider)

    csrf = await register_and_login(client, "missing_ingest_user@example.com")
    pdf_bytes = create_test_pdf("Test bytes.")

    res = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("disappearing.pdf", pdf_bytes, "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["processing_status"] == "FAILED"
    assert "PDF file not found in storage" in data["error_message"]
