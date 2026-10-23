import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from backend.app.core.config import settings

# Initialize Argon2 password hasher
ph = PasswordHasher()

ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    """Hash password using Argon2id with random salt."""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False

def create_session_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a cryptographically signed session JWT for HttpOnly cookie."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)

    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "session"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_session_token(token: str) -> Optional[dict]:
    """Decode and verify session JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "session":
            return None
        return payload
    except jwt.PyJWTError:
        return None

def generate_csrf_token(session_id: str) -> str:
    """Generate a HMAC-based CSRF token tied to the user's session identifier."""
    message = f"csrf:{session_id}"
    signature = hmac.new(
        settings.CSRF_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{session_id}.{signature}"

def verify_csrf_token(csrf_token: str, expected_session_id: str) -> bool:
    """Verify CSRF token using constant-time comparison against expected session ID."""
    if not csrf_token or "." not in csrf_token:
        return False
    
    parts = csrf_token.split(".", 1)
    if len(parts) != 2:
        return False
        
    token_session_id, signature = parts
    if not secrets.compare_digest(token_session_id, expected_session_id):
        return False

    expected_signature = hmac.new(
        settings.CSRF_SECRET.encode("utf-8"),
        f"csrf:{expected_session_id}".encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return secrets.compare_digest(signature, expected_signature)
