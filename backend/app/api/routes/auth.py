from fastapi import APIRouter, Depends, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.security import create_session_token, generate_csrf_token
from backend.app.db.session import get_db
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    CsrfTokenResponse,
)
from backend.app.services.auth_service import AuthService
from backend.app.api.dependencies import get_current_user
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

def set_session_cookie(response: Response, user_id: str, email: str) -> str:
    """Sets a secure, HttpOnly session cookie and returns the token string."""
    token = create_session_token(user_id=user_id, email=email)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return token

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account and initialize HttpOnly session."""
    user = await AuthService.register(
        db=db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    token = set_session_cookie(response, user.id, user.email)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        token=token,
    )

@router.post("/login", response_model=UserResponse)
async def login(
    payload: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate credentials and establish HttpOnly session."""
    user = await AuthService.authenticate(
        db=db,
        email=payload.email,
        password=payload.password
    )
    token = set_session_cookie(response, user.id, user.email)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        token=token,
    )

@router.post("/logout")
async def logout(response: Response):
    """Clear HttpOnly session cookie."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    return {"message": "Successfully logged out."}

@router.get("/me", response_model=UserResponse)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Retrieve profile and authentication status of the active session."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        token=token,
    )

@router.get("/csrf", response_model=CsrfTokenResponse)
async def get_csrf(current_user: User = Depends(get_current_user)):
    """Generate CSRF token tied to the current authenticated session."""
    token = generate_csrf_token(current_user.id)
    return CsrfTokenResponse(csrf_token=token)
