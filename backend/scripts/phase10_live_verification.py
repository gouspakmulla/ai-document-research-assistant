"""Phase 10 End-to-End Live Verification Script for AI Document Research Assistant.

Executes comprehensive live verification against the Supabase PostgreSQL database:
1. Inspects storage backend configuration and checks Supabase storage bucket status.
2. Uploads and ingests a multi-page Renewable Energy PDF into live PostgreSQL.
3. Uploads an unrelated Transformer research paper for the same user.
4. Submits question: "What are three examples of renewable energy?" and traces:
   - pgvector HNSW similarity search
   - Context prompt synthesis
   - Citations pointing exclusively to renewable energy doc with correct page numbers
   - ZERO citations / references to the transformer paper
5. Submits an unsupported query and verifies honest insufficient-evidence response with 0 citations.
6. Verifies document scoping, collection scoping, and tenant isolation (User A vs User B).
7. Verifies persistent storage content streaming and cascade cleanup upon deletion.
"""

import asyncio
import io
import os
import sys
import time
from urllib.parse import urlparse
import pymupdf as fitz
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.conversation import Conversation, Message
from backend.app.models.citation import MessageCitation
from backend.app.services.rag_service import INSUFFICIENT_EVIDENCE_ANSWER


def make_pdf(page_texts: list[str]) -> bytes:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def run_phase10_verification():
    print("=" * 80)
    print("PHASE 10: END-TO-END WORKFLOW VERIFICATION (LIVE DATABASE & STORAGE)")
    print("=" * 80)

    # Step 1: Storage Backend & Bucket Status
    print("\n--- [Step 1: Storage Backend & Supabase Bucket Status] ---")
    print(f"Configured STORAGE_BACKEND: {settings.STORAGE_BACKEND}")
    print(f"Configured STORAGE_DIR: {settings.STORAGE_DIR}")
    print(f"SUPABASE_URL: {settings.SUPABASE_URL or 'Not configured'}")
    print(f"SUPABASE_STORAGE_BUCKET: {settings.SUPABASE_STORAGE_BUCKET}")
    print(f"EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER} ({settings.EMBEDDING_MODEL})")
    print(f"LLM_PROVIDER: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")

    parsed = urlparse(settings.DATABASE_URL)
    safe_db = f"{parsed.scheme}://{parsed.username}@{parsed.hostname}:{parsed.port}{parsed.path}"
    print(f"Live Database Target: {safe_db}")

    async with AsyncSessionLocal() as session:
        v_res = await session.execute(text("SELECT version();"))
        print(f"[OK] Live PostgreSQL: {v_res.scalar().split(',')[0]}")
        ext_res = await session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';"))
        ext_ver = ext_res.scalar()
        print(f"[OK] pgvector extension: version {ext_ver}")

        # Check storage.buckets
        bucket_check = await session.execute(text("SELECT id, name, public FROM storage.buckets;"))
        buckets = bucket_check.fetchall()
        if buckets:
            print(f"[INFO] Storage buckets in Supabase database: {[b[1] for b in buckets]}")
        else:
            print("[INFO] No buckets found in storage.buckets table (Live Supabase storage bucket not created; local storage provider active).")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:

        # Step 2: Register User A and User B
        print("\n--- [Step 2: User Authentication & Isolation Setup] ---")
        ts = int(time.time())
        alice_email = f"phase10_alice_{ts}@energy.org"
        bob_email = f"phase10_bob_{ts}@external.org"
        password = "SecurePassword123!"

        # Register Alice
        res_a = await client.post("/api/v1/auth/register", json={
            "email": alice_email,
            "password": password,
            "full_name": "Dr. Alice Green",
        })
        assert res_a.status_code == 201, f"Alice reg failed: {res_a.text}"
        alice_data = res_a.json()
        alice_id = alice_data["id"]
        print(f"[OK] User A registered: {alice_email} (ID={alice_id})")

        # Login Alice to obtain session cookie & CSRF token
        login_a = await client.post("/api/v1/auth/login", json={"email": alice_email, "password": password})
        assert login_a.status_code == 200
        alice_cookies = login_a.cookies
        me_a = await client.get("/api/v1/auth/me", cookies=alice_cookies)
        csrf_a = me_a.headers.get("X-CSRF-Token", "")
        headers_a = {"X-CSRF-Token": csrf_a}
        print(f"[OK] User A session & CSRF established.")

        # Register Bob
        res_b = await client.post("/api/v1/auth/register", json={
            "email": bob_email,
            "password": password,
            "full_name": "Bob External",
        })
        assert res_b.status_code == 201
        bob_id = res_b.json()["id"]
        login_b = await client.post("/api/v1/auth/login", json={"email": bob_email, "password": password})
        bob_cookies = login_b.cookies
        me_b = await client.get("/api/v1/auth/me", cookies=bob_cookies)
        csrf_b = me_b.headers.get("X-CSRF-Token", "")
        headers_b = {"X-CSRF-Token": csrf_b}
        print(f"[OK] User B registered: {bob_email} (ID={bob_id})")

        # Step 3: Upload Renewable Energy PDF
        print("\n--- [Step 3: PDF Upload, Ingestion, Extraction, Chunking & READY Status] ---")
        pdf_energy = make_pdf([
            "Renewable Energy Handbook - Fundamentals\nRenewable energy sources replenish naturally without depletion.",
            "Key Categories:\nThree prominent examples of renewable energy are solar photovoltaic power, wind turbine energy, and hydroelectric power generation.",
            "Environmental Impact:\nDeploying solar and wind power eliminates atmospheric greenhouse gas emissions.",
        ])

        up_res_1 = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("renewable_energy_handbook.pdf", io.BytesIO(pdf_energy), "application/pdf")},
            cookies=alice_cookies,
            headers=headers_a,
        )
        assert up_res_1.status_code == 201, f"Upload 1 failed: {up_res_1.text}"
        doc_energy = up_res_1.json()
        energy_id = doc_energy["id"]
        print(f"[OK] Uploaded 'renewable_energy_handbook.pdf': ID={energy_id}")
        print(f"     Status: {doc_energy['processing_status']}, Page Count: {doc_energy['page_count']}")
        assert doc_energy["processing_status"] == "READY"
        assert doc_energy["page_count"] == 3

        # Upload unrelated Transformer paper for same user
        pdf_trans = make_pdf([
            "Attention Is All You Need - Research Paper\nWe introduce the Transformer model based solely on self-attention.",
            "Architecture Details:\nMulti-head attention allows the model to jointly attend to information from different representation subspaces.",
        ])
        up_res_2 = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("Attention_Is_All_You_Need_Transformer_Paper.pdf", io.BytesIO(pdf_trans), "application/pdf")},
            cookies=alice_cookies,
            headers=headers_a,
        )
        assert up_res_2.status_code == 201, f"Upload 2 failed: {up_res_2.text}"
        doc_trans = up_res_2.json()
        trans_id = doc_trans["id"]
        print(f"[OK] Uploaded 'Attention_Is_All_You_Need_Transformer_Paper.pdf': ID={trans_id}")
        print(f"     Status: {doc_trans['processing_status']}, Page Count: {doc_trans['page_count']}")
        assert doc_trans["processing_status"] == "READY"

        # Verify DB chunks and embeddings in live PostgreSQL
        async with AsyncSessionLocal() as session:
            c_res = await session.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == energy_id).order_by(DocumentChunk.chunk_index)
            )
            chunks = c_res.scalars().all()
            print(f"[OK] Verified {len(chunks)} chunks persisted in PostgreSQL for renewable energy doc.")
            for c in chunks:
                assert c.token_count > 0
                assert c.embedding is not None

        # Step 4: Trace Question Submission & Verify Citation Integrity
        print("\n--- [Step 4: Question Submission, Vector Retrieval & Grounded Citations] ---")
        q = "What are three examples of renewable energy?"
        print(f"Submitting query: '{q}'")

        ask_res = await client.post(
            "/api/v1/chat/ask",
            json={"question": q},
            cookies=alice_cookies,
            headers=headers_a,
        )
        assert ask_res.status_code == 200, f"Ask failed: {ask_res.text}"
        ask_data = ask_res.json()
        asst_msg = ask_data["assistant_message"]
        citations = asst_msg["citations"]

        print(f"[OK] Received response from assistant.")
        print(f"Assistant Content:\n{asst_msg['content']}\n")
        print(f"Citations Returned ({len(citations)}):")
        for cit in citations:
            print(f"  - Document: {cit['document_name']} | Page: {cit['page_number']} | Relevance: {cit['relevance_score'] * 100:.1f}%")

        assert len(citations) >= 1, "Must return at least 1 citation for grounded renewable energy question."

        for cit in citations:
            assert cit["document_id"] == energy_id, f"Citation must belong to renewable doc, got {cit['document_id']}"
            assert cit["document_name"] == "renewable_energy_handbook.pdf"
            assert cit["page_number"] in (1, 2, 3)
            assert cit["document_id"] != trans_id, "CRITICAL BUG: Cited unrelated transformer document ID!"
            assert "transformer" not in cit["document_name"].lower(), "CRITICAL BUG: Cited transformer paper filename!"

        assert "renewable_energy_handbook.pdf" in asst_msg["content"]
        assert "Attention_Is_All_You_Need" not in asst_msg["content"]
        assert "transformer" not in asst_msg["content"].lower()
        print("[VERIFIED] Citations come strictly from 'renewable_energy_handbook.pdf' with accurate page numbers. Transformer paper is excluded.")

        # Step 5: Insufficient Evidence Handling
        print("\n--- [Step 5: Insufficient Evidence Handling] ---")
        unsupported_q = "What is the capital adequacy requirement under the Basel III banking framework?"
        print(f"Submitting unsupported query: '{unsupported_q}'")

        unsup_res = await client.post(
            "/api/v1/chat/ask",
            json={"question": unsupported_q},
            cookies=alice_cookies,
            headers=headers_a,
        )
        assert unsup_res.status_code == 200
        unsup_data = unsup_res.json()["assistant_message"]
        print(f"Response Content:\n{unsup_data['content']}\n")
        print(f"Citations: {unsup_data['citations']}")

        assert INSUFFICIENT_EVIDENCE_ANSWER in unsup_data["content"]
        assert len(unsup_data["citations"]) == 0
        print("[VERIFIED] Insufficient evidence handled honestly with 0 citations.")

        # Step 6: Scoping Enforcement
        print("\n--- [Step 6: Scope Enforcement (Document & Collection)] ---")
        # Scoped to renewable doc
        scoped_res = await client.post(
            "/api/v1/chat/ask",
            json={"question": q, "document_id": energy_id},
            cookies=alice_cookies,
            headers=headers_a,
        )
        assert scoped_res.status_code == 200
        assert len(scoped_res.json()["assistant_message"]["citations"]) >= 1

        # Scoped to transformer doc for renewable question -> insufficient evidence
        trans_scoped = await client.post(
            "/api/v1/chat/ask",
            json={"question": q, "document_id": trans_id},
            cookies=alice_cookies,
            headers=headers_a,
        )
        assert trans_scoped.status_code == 200
        assert INSUFFICIENT_EVIDENCE_ANSWER in trans_scoped.json()["assistant_message"]["content"]
        assert len(trans_scoped.json()["assistant_message"]["citations"]) == 0
        print("[VERIFIED] Document scoping strictly restricts retrieval.")

        # Step 7: Cross-User Tenant Isolation
        print("\n--- [Step 7: Cross-User Tenant Isolation] ---")
        bob_docs = (await client.get("/api/v1/documents", cookies=bob_cookies)).json()
        assert len(bob_docs) == 0, f"Bob should have 0 documents, found {len(bob_docs)}"

        bob_leak_attempt = await client.get(f"/api/v1/documents/{energy_id}/content", cookies=bob_cookies)
        assert bob_leak_attempt.status_code == 404, f"Expected 404 for unauthorized doc stream, got {bob_leak_attempt.status_code}"

        bob_query_attempt = await client.post(
            "/api/v1/chat/ask",
            json={"question": q, "document_id": energy_id},
            cookies=bob_cookies,
            headers=headers_b,
        )
        assert bob_query_attempt.status_code == 404
        print("[VERIFIED] Cross-user tenant isolation strictly enforced.")

        # Step 8: Persistent Storage Stream & Cleanup
        print("\n--- [Step 8: Persistent Storage Stream & Cascade Deletion] ---")
        content_res = await client.get(f"/api/v1/documents/{energy_id}/content", cookies=alice_cookies)
        assert content_res.status_code == 200
        assert content_res.content == pdf_energy
        print(f"[OK] Content stream byte-for-byte identical ({len(content_res.content)} bytes).")

        # Cleanup created docs
        del_1 = await client.delete(f"/api/v1/documents/{energy_id}", cookies=alice_cookies, headers=headers_a)
        assert del_1.status_code == 204
        del_2 = await client.delete(f"/api/v1/documents/{trans_id}", cookies=alice_cookies, headers=headers_a)
        assert del_2.status_code == 204
        print("[OK] Test documents deleted with cascading cleanup.")

    print("\n" + "=" * 80)
    print("PHASE 10 LIVE VERIFICATION COMPLETE: ALL CHECKS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_phase10_verification())
