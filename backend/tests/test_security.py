import pytest
from datetime import timedelta
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_session_token,
    decode_session_token,
    generate_csrf_token,
    verify_csrf_token,
)

def test_password_hashing():
    raw_pass = "superSecretPassword123!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert hashed.startswith("$argon2")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("wrongPassword123!", hashed) is False

def test_session_token_lifecycle():
    user_id = "user-uuid-123"
    email = "test@research.edu"

    token = create_session_token(user_id=user_id, email=email)
    assert isinstance(token, str)

    payload = decode_session_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == email

    # Test expired token
    expired_token = create_session_token(user_id=user_id, email=email, expires_delta=timedelta(seconds=-10))
    expired_payload = decode_session_token(expired_token)
    assert expired_payload is None

def test_csrf_token_verification():
    user_id = "session-test-id"
    csrf = generate_csrf_token(user_id)
    assert verify_csrf_token(csrf, user_id) is True
    assert verify_csrf_token(csrf, "different-session-id") is False
    assert verify_csrf_token("invalid.token.format", user_id) is False
