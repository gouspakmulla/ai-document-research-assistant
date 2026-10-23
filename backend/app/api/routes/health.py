from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db

router = APIRouter(prefix="", tags=["Health"])

@router.get("/health")
async def health_check():
    """Liveness probe to confirm FastAPI service is responding."""
    return {"status": "healthy", "service": "AI Document Research Assistant"}

@router.get("/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Readiness probe checking active database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity failed: {str(e)}"
        )
