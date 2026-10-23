import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.main import app
from backend.app.db.session import get_db

@pytest.mark.asyncio
async def test_tenant_data_isolation(test_db_session: AsyncSession):
    """Verify that User B cannot access or modify User A's collections or conversations."""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    # 1. User A session
    async with AsyncClient(transport=transport, base_url="http://testserver") as client_a:
        res_a = await client_a.post("/api/v1/auth/register", json={
            "email": "user_a@research.edu",
            "password": "Password123!",
            "full_name": "User Alpha"
        })
        assert res_a.status_code == 201

        # User A creates a collection
        col_res = await client_a.post("/api/v1/collections", json={
            "name": "User A Private Research",
            "description": "Sensitive papers"
        })
        assert col_res.status_code == 201
        col_a_id = col_res.json()["id"]

        # User A creates a conversation
        conv_res = await client_a.post("/api/v1/chat/conversations", json={
            "title": "Confidential Inquiry",
            "collection_id": col_a_id
        })
        assert conv_res.status_code == 201
        conv_a_id = conv_res.json()["id"]

    # 2. User B session (distinct client / cookies)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client_b:
        res_b = await client_b.post("/api/v1/auth/register", json={
            "email": "user_b@research.edu",
            "password": "Password123!",
            "full_name": "User Beta"
        })
        assert res_b.status_code == 201

        # User B lists collections -> should be empty
        b_cols = await client_b.get("/api/v1/collections")
        assert b_cols.status_code == 200
        assert len(b_cols.json()) == 0

        # User B attempts to delete User A's collection -> must return 404
        bad_del = await client_b.delete(f"/api/v1/collections/{col_a_id}")
        assert bad_del.status_code == 404

        # User B lists conversations -> should be empty
        b_convs = await client_b.get("/api/v1/chat/conversations")
        assert b_convs.status_code == 200
        assert len(b_convs.json()) == 0

        # User B attempts to access messages of User A's conversation -> must return 404
        bad_msg = await client_b.get(f"/api/v1/chat/conversations/{conv_a_id}/messages")
        assert bad_msg.status_code == 404

        # User B attempts to delete User A's conversation -> must return 404
        bad_del_conv = await client_b.delete(f"/api/v1/chat/conversations/{conv_a_id}")
        assert bad_del_conv.status_code == 404

    app.dependency_overrides.clear()
