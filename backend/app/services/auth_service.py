from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.app.models.user import User
from backend.app.repositories.user_repo import UserRepository
from backend.app.core.security import hash_password, verify_password, create_session_token, decode_session_token

class AuthService:
    @staticmethod
    async def register(db: AsyncSession, email: str, password: str, full_name: Optional[str] = None) -> User:
        existing = await UserRepository.get_by_email(db, email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists."
            )
        
        hashed = hash_password(password)
        user = await UserRepository.create(db, email=email, hashed_password=hashed, full_name=full_name)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User:
        user = await UserRepository.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated."
            )
        return user

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> Optional[User]:
        payload = decode_session_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = await UserRepository.get_by_id(db, user_id)
        if not user or not user.is_active:
            return None
        return user

auth_service = AuthService()
