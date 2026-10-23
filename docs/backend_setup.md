# Backend Setup & Database Guide

## 1. Prerequisites & Virtual Environment

The backend is built with Python 3.12+ (tested through 3.14 on Windows) using FastAPI and asynchronous SQLAlchemy 2.0.

```powershell
# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r backend\requirements.txt
```

---

## 2. Database Options (PostgreSQL + pgvector)

The backend connects to PostgreSQL using the async driver `asyncpg` and uses `pgvector` for vector similarity search.

### Option A: Local PostgreSQL with pgvector
1. Install PostgreSQL 16+.
2. Install the `pgvector` extension (e.g. from GitHub or binary packages).
3. Connect with `psql` and enable the extension:
   ```sql
   CREATE DATABASE doc_assistant;
   \c doc_assistant
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Set `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/doc_assistant
   ```

### Option B: Cloud PostgreSQL (Neon, Supabase, Aiven, AWS RDS)
All major cloud Postgres providers come with `pgvector` pre-installed:
```env
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<dbname>?ssl=require
```

### Option C: Docker Container (when Docker is installed)
```bash
docker run -d --name doc-assistant-pg -p 5432:5432 -e POSTGRES_DB=doc_assistant -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
```

---

## 3. Database Migrations (Alembic)

Alembic manages schema versioning and automatically ensures `CREATE EXTENSION IF NOT EXISTS vector;` is executed.

```powershell
# Run all pending migrations
.\.venv\Scripts\alembic.exe -c backend\alembic.ini upgrade head

# Rollback last migration
.\.venv\Scripts\alembic.exe -c backend\alembic.ini downgrade -1
```

---

## 4. Running the Development Backend Server

```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger OpenAPI docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Readiness check: `http://127.0.0.1:8000/ready`

---

## 5. Running Automated Backend Tests

The test suite in `backend/tests/` uses an isolated in-memory SQLite async engine with transactional rollbacks, allowing complete offline execution:

```powershell
.\.venv\Scripts\pytest.exe backend/tests -v
```

Verified test coverage (55 automated tests passed):
1. `test_auth.py`: User registration, duplicate validation, password complexity, login, session cookies, and logout.
2. `test_security.py`: Argon2 password hashing, JWT session expiration, HMAC CSRF verification.
3. `test_isolation.py`: Strict multi-tenant isolation guaranteeing User B cannot list, query, or delete User A's collections or conversations.
4. `test_chunking.py`: Page-aware recursive chunking, boundary splitting, overlap preservation, empty page skipping, and page number accuracy.
5. `test_pdf_service.py`: PyMuPDF page-by-page text extraction, scanned PDF detection, corrupted files, and password protection handling.
6. `test_documents.py`: Secure PDF upload validation (magic bytes, MIME types, extensions, size limits), pipeline transitions (PENDING -> EXTRACTING -> CHUNKING -> EMBEDDING -> READY / OCR_REQUIRED / FAILED), embedding failure recovery, tenant authorization isolation, and PDF content streaming.
7. `test_embedding.py`: Mock, OpenAI, and Gemini embedding providers, vector dimension enforcement (1536), batching with deduplication, retry with exponential backoff on 429/5xx, and provider factory fallback.
8. `test_retrieval.py`: pgvector cosine similarity ranking, top-K selection, similarity threshold filtering, strict tenant isolation (User B cannot retrieve User A's chunks), document/collection scoping, unready document omission, and search API endpoint (`POST /api/v1/search`).
9. `test_rag.py`: Mock, OpenAI, and Gemini LLM provider selection and validation, grounded answer synthesis, insufficient-evidence gate, citation resolution and invalid citation filtering, prompt injection defense, transaction rollback on model failure, conversation persistence, and CSRF protection.

---

## 6. Document Ingestion & PDF Processing Pipeline (Phase 4)

- **Upload Endpoint**: `POST /api/v1/documents/upload`
  - Validates `%PDF-` header signature, extension (`.pdf`), MIME types, and configurable file size limits (`MAX_FILE_SIZE_MB`).
  - Generates secure UUID storage paths outside the web root (`STORAGE_DIR`).
- **Processing Statuses**: `PENDING`, `EXTRACTING`, `CHUNKING`, `EMBEDDING`, `READY`, `FAILED`, `OCR_REQUIRED`.
- **Text Extraction**: Uses PyMuPDF (`fitz`) to extract structured text page by page with exact 1-indexed page provenance.
- **Scanned PDF Handling**: Documents with insufficient extractable text are flagged `OCR_REQUIRED` rather than indexing blank content.
- **Recursive Chunking**: Configurable ~800 char chunk size and ~150 char overlap with page-level citation boundaries.
- **PDF Viewing**: Authenticated streaming at `GET /api/v1/documents/{id}/content` with `inline` disposition.

---

## 7. Embedding Service, pgvector Semantic Retrieval & Search (Phase 5)

### 7.1 Provider Pattern
- **Supported Providers**: `mock` (default offline/test), `openai` (`text-embedding-3-small`), `gemini` (`text-embedding-004`).
- **Dimension Enforcement**: Strictly validates generated vectors match `EMBEDDING_DIMENSION` (1536).
- **Batching & Resilience**: Batch-processes chunks (default 50) with in-memory deduplication and exponential backoff retry.

### 7.2 Semantic Search API
- **Endpoint**: `POST /api/v1/search`
  - **Body**: `{ "query": "string", "document_id": "optional", "collection_id": "optional", "top_k": 6, "similarity_threshold": 0.6 }`
  - Strict tenant filtering (`user_id = current_user.id`), scoping, and status checks (`READY` only).

### 7.3 PostgreSQL & pgvector Integration Status
- **Alembic Migrations**:
  - `001_initial_schema`: Base tables with `pgvector` Vector(1536) column on `document_chunks`.
  - `002_vector_hnsw_index`: Creates HNSW vector index (`vector_cosine_ops`) for high-performance approximate nearest neighbor search.
- **Environment Status**: Live connection probe to `localhost:5432` timed out because a local PostgreSQL service is not running on this host. Consequently, all 55 automated backend tests execute in-memory with the async test harness. Once PostgreSQL with pgvector is launched (e.g. via Docker: `docker run -d -p 5432:5432 -e POSTGRES_DB=doc_assistant -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16`), run:
  ```powershell
  .\.venv\Scripts\alembic.exe -c backend\alembic.ini upgrade head
  ```

---

## 8. Grounded RAG, Citations & AI Chat Engine (Phase 6)

### 8.1 LLM Provider Configuration
Select the language model provider in `.env` using `LLM_PROVIDER`:
- **`mock`** (Default): Deterministic, offline, zero-cost synthesis. Accurately simulates grounded answers with source citations, enforces anti-injection defenses, and clearly marks answers with `[Mock AI Response]` and footer so mock responses are never silently presented as real AI.
- **`openai`**: Chat Completions (`gpt-4o-mini`, `gpt-4o`, etc.) using `httpx` with timeout (30s) and exponential backoff on 429/5xx. Requires `OPENAI_API_KEY`.
- **`gemini`**: Google Generative AI REST API (`gemini-1.5-flash`, etc.) with retries. Requires `GEMINI_API_KEY`.

### 8.2 Grounded RAG Pipeline Workflow
1. **User Authentication & Tenant Check**: Extract user from session cookie or Bearer header.
2. **Scope Validation**: If `document_id` or `collection_id` is supplied, verify tenant ownership and `READY` status.
3. **Query Embedding**: Embed user question using Phase 5 `embedding_service`.
4. **Semantic Retrieval**: Retrieve top-K chunks meeting similarity threshold using `retrieval_service.search`.
5. **Evidence Gating**: If zero chunks meet threshold, immediately return honest insufficient-evidence response (`"I do not have sufficient evidence in the uploaded documents to answer this question."`) with empty citations, without calling the LLM.
6. **Anti-Injection Context Construction**: Sanitize chunk text to neutralize boundary tag collisions, wrapping chunks in `<context_documents>` with strict system instructions treating documents as untrusted data.
7. **Citation Resolution**: Parse citations (`[Source X]`, `[X]`, etc.) from the LLM output and resolve exclusively against actual retrieved chunks. Reject any fabricated or out-of-context references.
8. **Transactional Persistence**: Persist `Conversation`, user `Message`, assistant `Message`, and `MessageCitation` records inside a single database transaction with automatic rollback on error.

### 8.3 Chat Endpoints
- `GET /api/v1/chat/conversations`: List user's conversations with message counts and collection names.
- `POST /api/v1/chat/conversations`: Create a new conversation session (`X-CSRF-Token` required for cookie sessions).
- `GET /api/v1/chat/conversations/{id}`: Retrieve single conversation details.
- `DELETE /api/v1/chat/conversations/{id}`: Delete conversation and cascade-delete messages/citations.
- `GET /api/v1/chat/conversations/{id}/messages`: Retrieve conversation history with structured citations.
- `POST /api/v1/chat/ask`: Execute Grounded RAG inquiry.
  - **Request Body**:
    ```json
    {
      "question": "What are the primary theoretical contributions presented in this document?",
      "conversation_id": "optional-uuid",
      "document_id": "optional-uuid",
      "collection_id": "optional-uuid"
    }
    ```
  - **Response Body**:
    ```json
    {
      "conversation_id": "060d5bfa-c4ae-4db1-9aa2-601e3e7f41cf",
      "user_message": {
        "id": "msg-1",
        "conversation_id": "060d5bfa-c4ae-4db1-9aa2-601e3e7f41cf",
        "role": "user",
        "content": "What are the primary theoretical contributions presented in this document?",
        "created_at": "2026-10-20T14:30:00Z",
        "citations": []
      },
      "assistant_message": {
        "id": "msg-2",
        "conversation_id": "060d5bfa-c4ae-4db1-9aa2-601e3e7f41cf",
        "role": "assistant",
        "content": "Based on the verified document evidence, the primary contribution is... [Source 1]",
        "created_at": "2026-10-20T14:30:01Z",
        "citations": [
          {
            "id": "cit-1",
            "message_id": "msg-2",
            "document_id": "doc-uuid",
            "chunk_id": "chk-uuid",
            "document_name": "neural_nets.pdf",
            "page_number": 3,
            "snippet": "Convolutional networks utilize shared weights...",
            "relevance_score": 0.92,
            "created_at": "2026-10-20T14:30:01Z"
          }
        ]
      }
    }
    ```



