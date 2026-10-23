import asyncio
import sys
import os
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Ensure root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.app.core.config import settings


async def verify():
    url = settings.DATABASE_URL
    print(f"Checking configuration DATABASE_URL...")

    if "[YOUR-PASSWORD]" in url:
        print("[ERROR] DATABASE_URL in .env still contains '[YOUR-PASSWORD]'.")
        print("Please replace '[YOUR-PASSWORD]' in .env with your actual Supabase database password.")
        sys.exit(1)

    # Obfuscate password in printed URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    safe_netloc = parsed.netloc
    if parsed.password:
        safe_netloc = safe_netloc.replace(f":{parsed.password}@", ":****@")
    print(f"Connecting to {parsed.scheme}://{safe_netloc}{parsed.path} (SSL enabled)...")

    engine = create_async_engine(url, pool_pre_ping=True)

    try:
        async with engine.connect() as conn:
            # 1. Connectivity & Version
            version_res = await conn.execute(text("SELECT version();"))
            db_version = version_res.scalar()
            print(f"[OK] Connected successfully!")
            print(f"     PostgreSQL Version: {db_version.split(',')[0]}")

            db_info = await conn.execute(text("SELECT current_database(), current_user;"))
            curr_db, curr_user = db_info.first()
            print(f"     Database: {curr_db} | User: {curr_user}")

            # 2. Vector Extension
            vec_check = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';"))
            vec_version = vec_check.scalar()
            if vec_version:
                print(f"[OK] pgvector extension is ENABLED (version: {vec_version})")
            else:
                print("[INFO] pgvector extension not yet enabled. Enabling now...")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                await conn.commit()
                vec_check2 = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';"))
                v2 = vec_check2.scalar()
                print(f"[OK] pgvector extension successfully enabled (version: {v2})")

            # 3. Check Tables
            tables_res = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
            ))
            tables = [r[0] for r in tables_res.fetchall()]
            print(f"[INFO] Existing public tables: {tables if tables else 'None (ready for migrations)'}")

            # 4. If document_chunks exists, check embedding column and HNSW index
            if "document_chunks" in tables:
                col_res = await conn.execute(text(
                    "SELECT column_name, data_type, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'document_chunks' AND column_name = 'embedding';"
                ))
                col = col_res.first()
                dim_res = await conn.execute(text(
                    "SELECT atttypmod FROM pg_attribute "
                    "WHERE attrelid = 'document_chunks'::regclass AND attname = 'embedding';"
                ))
                dim = dim_res.scalar()
                print(f"[OK] document_chunks.embedding column: data_type={col[1]}, udt_name={col[2]}, dimension={dim}")

                # Check index
                idx_res = await conn.execute(text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE tablename = 'document_chunks' AND indexname = 'ix_document_chunks_embedding_hnsw';"
                ))
                idx = idx_res.first()
                if idx:
                    print(f"[OK] HNSW vector index verified: {idx[0]}")
                    print(f"     Definition: {idx[1]}")
                else:
                    print("[INFO] HNSW index not yet created (will be created by migration 002).")

    except Exception as e:
        print(f"[FAIL] Database connection error: {e}")
        sys.exit(2)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify())
