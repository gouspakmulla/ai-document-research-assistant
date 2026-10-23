from typing import Optional
from fastapi import Depends, Request, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.security import verify_csrf_token
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.services.auth_service import AuthService

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and authenticate current user via HttpOnly session cookie."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        # Also check Authorization header as fallback for API tools/testing
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session required.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    user = await AuthService.get_current_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    return user

async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Optionally return authenticated user without throwing 401."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()
    if not token:
        return None
    return await AuthService.get_current_user(db, token)

def require_csrf(
    request: Request,
    current_user: User = Depends(get_current_user),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token")
):
    """Enforce CSRF token verification on state-changing requests."""
    # Skip CSRF check in safe methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # In development/test mode, if no CSRF token header is sent, allow if explicitly configured
    if not x_csrf_token:
        # Allow Bearer token clients (like programmatic tests or curl) to bypass cookie-CSRF checks
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return
        if settings.ENVIRONMENT in ("testing", "development"):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required CSRF token (X-CSRF-Token header)."
        )

    if not verify_csrf_token(x_csrf_token, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired CSRF token."
        )
