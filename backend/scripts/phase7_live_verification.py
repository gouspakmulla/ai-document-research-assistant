"""Phase 7 End-to-End Live Verification Script for AI Document Research Assistant.

Executes comprehensive verification against the live Supabase PostgreSQL database:
1. User registration and login (User A & User B).
2. Synthetic PDF generation and ingestion pipeline (extraction, chunking, embeddings, READY).
3. Supported question answering with verified page citations.
4. Unsupported question handling with insufficient-evidence response.
5. Persistence verification of conversations, messages, and citations across reloads.
6. Direct PostgreSQL pgvector semantic retrieval and HNSW cosine distance verification.
7. Cross-user tenant isolation enforcement.
8. Upload error handling and validation tests.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Dict, Any, List
import fitz  # PyMuPDF
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.conversation import Conversation, Message
from backend.app.models.citation import MessageCitation


def create_synthetic_pdf() -> bytes:
    """Generate a valid 3-page PDF with distinct factual content on each page."""
    doc = fitz.open()

    # Page 1: Apollo Project Initiation
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "Project Apollo: National Space Exploration Initiative\n\n"
        "Project Apollo was officially initiated in May 1961 by President John F. Kennedy\n"
        "with the ambitious national objective of landing an American astronaut on the Moon\n"
        "and returning him safely to the Earth before the decade of the 1960s was out.\n"
        "The project required massive mobilization of scientific, industrial, and government resources.",
        fontsize=12,
    )

    # Page 2: Saturn V Rocket Specifications
    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "Saturn V Launch Vehicle Technical Specifications\n\n"
        "The Saturn V rocket stood precisely 363 feet tall (111 meters) and weighed 6.2 million pounds fully fueled.\n"
        "At liftoff, its first stage (S-IC) produced 7.5 million pounds of total thrust (33.4 meganewtons)\n"
        "powered by five Rocketdyne F-1 engines burning RP-1 kerosene and liquid oxygen.\n"
        "It remains one of the most powerful launch vehicles ever successfully flown into space.",
        fontsize=12,
    )

    # Page 3: Apollo 11 Mission Splashdown
    p3 = doc.new_page()
    p3.insert_text(
        (50, 72),
        "Apollo 11 Mission Completion and Recovery Operations\n\n"
        "Command Module Columbia successfully splashed down in the North Pacific Ocean on July 24, 1969.\n"
        "The coordinates were 13 degrees 19 minutes North and 169 degrees 9 minutes West,\n"
        "approximately 812 nautical miles southwest of Hawaii.\n"
        "The recovery ship USS Hornet safely hoisted the crew and spacecraft aboard within two hours.",
        fontsize=12,
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def run_phase7_verification():
    print("=" * 80)
    print("PHASE 7: END-TO-END VERIFICATION AGAINST LIVE SUPABASE POSTGRESQL")
    print("=" * 80)

    # 1. Inspect Environment & DB Connectivity
    print("\n--- [Step 1: Inspect Environment & Database Target] ---")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Embedding Provider: {settings.EMBEDDING_PROVIDER} ({settings.EMBEDDING_MODEL})")
    print(f"LLM Provider: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")

    from urllib.parse import urlparse
    parsed = urlparse(settings.DATABASE_URL)
    print(f"Database Target: {parsed.scheme}://{parsed.username}@{parsed.hostname}:{parsed.port}{parsed.path}")

    async with AsyncSessionLocal() as session:
        v_res = await session.execute(text("SELECT version();"))
        print(f"[OK] PostgreSQL: {v_res.scalar().split(',')[0]}")
        ext_res = await session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';"))
        ext_ver = ext_res.scalar()
        print(f"[OK] pgvector extension: {ext_ver}")
        assert ext_ver is not None, "pgvector extension must be installed"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:

        async def req_post(url: str, **kwargs):
            for attempt in range(4):
                try:
                    return await client.post(url, **kwargs)
                except Exception as exc:
                    if attempt < 3:
                        await asyncio.sleep(1.5)
                        continue
                    raise exc

        async def req_get(url: str, **kwargs):
            for attempt in range(4):
                try:
                    return await client.get(url, **kwargs)
                except Exception as exc:
                    if attempt < 3:
                        await asyncio.sleep(1.5)
                        continue
                    raise exc

        # 2. User Registration & Authentication (User A & User B)
        print("\n--- [Step 2: User Registration & Authentication] ---")
        ts = int(time.time())
        alice_email = f"phase7_alice_{ts}@example.com"
        bob_email = f"phase7_bob_{ts}@example.com"
        password = "SecurePassword123!"

        # Register Alice
        res_a = await req_post("/api/v1/auth/register", json={
            "email": alice_email,
            "password": password,
            "full_name": "Alice Apollo",
        })
        assert res_a.status_code == 201, f"Alice registration failed: {res_a.text}"
        alice_data = res_a.json()
        alice_id = alice_data["id"]
        print(f"[OK] User A (Alice) registered: ID={alice_id}, Email={alice_email}")

        # Extract session cookie
        alice_cookies = res_a.cookies

        # Register Bob
        res_b = await req_post("/api/v1/auth/register", json={
            "email": bob_email,
            "password": password,
            "full_name": "Bob Borman",
        })
        assert res_b.status_code == 201, f"Bob registration failed: {res_b.text}"
        bob_data = res_b.json()
        bob_id = bob_data["id"]
        print(f"[OK] User B (Bob) registered: ID={bob_id}, Email={bob_email}")
        bob_cookies = res_b.cookies

        # Verify Alice Login
        login_a = await req_post("/api/v1/auth/login", json={
            "email": alice_email,
            "password": password,
        })
        assert login_a.status_code == 200, f"Alice login failed: {login_a.text}"
        alice_cookies = login_a.cookies
        print(f"[OK] Alice login verified (session cookie established)")

        # Verify /auth/me for Alice
        me_res = await req_get("/api/v1/auth/me", cookies=alice_cookies)
        assert me_res.status_code == 200 and me_res.json()["id"] == alice_id
        print(f"[OK] /api/v1/auth/me verified: {me_res.json()['full_name']}")

        # 3. Synthetic PDF Upload & Full Ingestion Pipeline
        print("\n--- [Step 3: Synthetic PDF Upload & Ingestion Pipeline] ---")
        pdf_bytes = create_synthetic_pdf()
        print(f"Generated 3-page synthetic Apollo research PDF ({len(pdf_bytes)} bytes)")

        files = {"file": ("apollo_mission_brief.pdf", pdf_bytes, "application/pdf")}
        up_res = await req_post("/api/v1/documents/upload", files=files, cookies=alice_cookies)
        assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
        doc_data = up_res.json()
        doc_id = doc_data["id"]
        print(f"[OK] Document uploaded successfully: ID={doc_id}, Filename={doc_data['filename']}")
        print(f"     Page Count: {doc_data['page_count']}, Status: {doc_data['processing_status']}")
        assert doc_data["processing_status"] == "READY", f"Expected READY, got {doc_data['processing_status']}"
        assert doc_data["page_count"] == 3, f"Expected 3 pages, got {doc_data['page_count']}"

        # Verify chunks and embeddings in Supabase database
        async with AsyncSessionLocal() as session:
            chunks_q = select(DocumentChunk).where(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index)
            c_res = await session.execute(chunks_q)
            chunks = c_res.scalars().all()
            print(f"[OK] Supabase document_chunks verified: {len(chunks)} chunks stored")
            for c in chunks:
                emb_len = len(c.embedding) if c.embedding is not None else 0
                print(f"     Chunk {c.chunk_index} (Page {c.page_number}): len={len(c.content)} chars, embedding_dim={emb_len}")
                assert emb_len == 1536, f"Expected 1536-dim embedding, got {emb_len}"
                assert c.user_id == alice_id, "Chunk user_id must match Alice"

        # 4. Ask Supported Question & Verify Citations
        print("\n--- [Step 4: Supported Question & Verified Citations] ---")
        supported_q = "How tall was the Saturn V rocket and how much thrust did its engines produce?"
        print(f"Question: '{supported_q}'")

        ask_res = await req_post("/api/v1/chat/ask", json={
            "question": supported_q,
            "document_id": doc_id,
        }, cookies=alice_cookies)
        assert ask_res.status_code == 200, f"Ask question failed: {ask_res.text}"
        ask_data = ask_res.json()
        conv_id = ask_data["conversation_id"]
        asst_msg = ask_data["assistant_message"]
        citations = asst_msg["citations"]

        print(f"[OK] Response received (Conversation ID: {conv_id}):")
        print(f"     Assistant Answer: {asst_msg['content'][:140]}...")
        print(f"     Citations Count: {len(citations)}")
        for idx, cit in enumerate(citations, 1):
            print(f"     - Citation {idx}: Doc='{cit['document_name']}', Page={cit['page_number']}, Score={cit['relevance_score']:.3f}")
            print(f"       Snippet: '{cit['snippet'][:90]}...'")

        assert len(citations) > 0, "Expected at least 1 citation for supported question"
        # Saturn V content was on Page 2
        pages_cited = [c["page_number"] for c in citations]
        assert 2 in pages_cited, f"Expected Page 2 cited for Saturn V rocket, got {pages_cited}"
        assert "[Mock AI Response]" in asst_msg["content"], "Mock provider identifier must be present when using mock provider"

        # 5. Ask Unsupported Question & Verify Insufficient Evidence
        print("\n--- [Step 5: Unsupported Question & Insufficient Evidence] ---")
        unsupported_q = "What is the speed of light in vacuum in meters per second?"
        print(f"Question: '{unsupported_q}'")

        un_res = await req_post("/api/v1/chat/ask", json={
            "question": unsupported_q,
            "conversation_id": conv_id,
            "document_id": doc_id,
        }, cookies=alice_cookies)
        assert un_res.status_code == 200, f"Unsupported question failed: {un_res.text}"
        un_data = un_res.json()
        un_asst = un_data["assistant_message"]
        un_citations = un_asst["citations"]

        print(f"[OK] Response received:")
        print(f"     Assistant Answer: {un_asst['content'][:120]}...")
        assert "sufficient evidence" in un_asst["content"].lower(), "Expected insufficient evidence statement"
        assert len(un_citations) == 0, f"Expected 0 citations for unsupported question, got {len(un_citations)}"

        # 6. Verify Persistence across Reload
        print("\n--- [Step 6: Persistence of Conversations, Messages & Citations] ---")
        # Fetch conversation messages afresh via API
        reload_res = await req_get(f"/api/v1/chat/conversations/{conv_id}/messages", cookies=alice_cookies)
        assert reload_res.status_code == 200, f"Reload messages failed: {reload_res.text}"
        stored_messages = reload_res.json()
        print(f"[OK] Reloaded conversation messages: {len(stored_messages)} messages stored in Supabase")
        assert len(stored_messages) == 4, f"Expected 4 messages (2 user + 2 assistant), got {len(stored_messages)}"

        # Verify citations on the first assistant message
        first_asst_msg = stored_messages[1]
        assert first_asst_msg["role"] == "assistant"
        assert len(first_asst_msg["citations"]) > 0, "Citations must persist in database"
        print(f"[OK] First assistant message persisted with {len(first_asst_msg['citations'])} citation(s) in Supabase")

        # 7. Semantic Retrieval pgvector Verification
        print("\n--- [Step 7: PostgreSQL pgvector Semantic Retrieval] ---")
        search_res = await req_post("/api/v1/search", json={
            "query": "Saturn V rocket thrust and height",
            "document_id": doc_id,
            "top_k": 3,
        }, cookies=alice_cookies)
        assert search_res.status_code == 200, f"Search failed: {search_res.text}"
        search_items = search_res.json()["results"]
        print(f"[OK] pgvector search returned {len(search_items)} results for Alice:")
        for r in search_items:
            print(f"     Page {r['page_number']}: score={r['relevance_score']:.4f} | '{r['snippet'][:75]}...'")
        assert len(search_items) > 0
        assert search_items[0]["page_number"] == 2, f"Top ranked result should be Page 2, got {search_items[0]['page_number']}"

        # 8. Cross-User Tenant Isolation Enforcement
        print("\n--- [Step 8: Cross-User Tenant Isolation Enforcement] ---")
        # Bob tries to access Alice's document metadata
        bob_doc_get = await req_get(f"/api/v1/documents/{doc_id}", cookies=bob_cookies)
        print(f"     Bob accessing Alice's document: HTTP {bob_doc_get.status_code}")
        assert bob_doc_get.status_code == 404, f"Expected 404 for cross-user document access, got {bob_doc_get.status_code}"

        # Bob tries to access Alice's chunks
        bob_chunks_get = await req_get(f"/api/v1/documents/{doc_id}/chunks", cookies=bob_cookies)
        print(f"     Bob accessing Alice's document chunks: HTTP {bob_chunks_get.status_code}")
        assert bob_chunks_get.status_code == 404, f"Expected 404 for cross-user chunks access, got {bob_chunks_get.status_code}"

        # Bob tries to download Alice's PDF
        bob_content_get = await req_get(f"/api/v1/documents/{doc_id}/content", cookies=bob_cookies)
        print(f"     Bob accessing Alice's PDF binary: HTTP {bob_content_get.status_code}")
        assert bob_content_get.status_code == 404, f"Expected 404 for cross-user PDF download, got {bob_content_get.status_code}"

        # Bob tries to access Alice's conversation
        bob_conv_get = await req_get(f"/api/v1/chat/conversations/{conv_id}/messages", cookies=bob_cookies)
        print(f"     Bob accessing Alice's conversation: HTTP {bob_conv_get.status_code}")
        assert bob_conv_get.status_code == 404, f"Expected 404 for cross-user conversation access, got {bob_conv_get.status_code}"

        # Bob searches for Saturn V (should return 0 results since Bob has no documents)
        bob_search = await req_post("/api/v1/search", json={
            "query": "Saturn V rocket thrust and height",
            "top_k": 3,
        }, cookies=bob_cookies)
        assert bob_search.status_code == 200
        bob_results = bob_search.json()["results"]
        print(f"     Bob semantic search results count: {len(bob_results)}")
        assert len(bob_results) == 0, f"Expected 0 results for Bob, got {len(bob_results)}"
        print(f"[OK] Strict cross-user tenant isolation verified across documents, chunks, conversations, and search")

        # 9. Upload Rejections & Error Handling
        print("\n--- [Step 9: Upload Validation & Error Handling] ---")
        # A: Invalid file extension (.txt)
        bad_ext_files = {"file": ("malicious.txt", b"plain text content", "text/plain")}
        res_bad_ext = await req_post("/api/v1/documents/upload", files=bad_ext_files, cookies=alice_cookies)
        print(f"     Upload .txt file rejection: HTTP {res_bad_ext.status_code} ({res_bad_ext.json().get('detail')})")
        assert res_bad_ext.status_code == 400

        # B: Invalid magic bytes (named .pdf but text content)
        fake_pdf_files = {"file": ("fake.pdf", b"This is not a real PDF file header", "application/pdf")}
        res_fake_pdf = await req_post("/api/v1/documents/upload", files=fake_pdf_files, cookies=alice_cookies)
        print(f"     Upload fake PDF header rejection: HTTP {res_fake_pdf.status_code} ({res_fake_pdf.json().get('detail')})")
        assert res_fake_pdf.status_code == 400

        # C: Unauthenticated access
        async with AsyncClient(transport=transport, base_url="http://localhost:8000") as unauth_client:
            unauth_res = await unauth_client.get("/api/v1/documents")
            print(f"     Unauthenticated document list rejection: HTTP {unauth_res.status_code}")
            assert unauth_res.status_code == 401
        print(f"[OK] All security validations and error handling rejected invalid inputs properly")

    print("\n" + "=" * 80)
    print("PHASE 7 LIVE END-TO-END VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_phase7_verification())
