"""Debug endpoint to test AI config dependencies."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_async_db
from app.dependencies import CurrentUserRequired
from app.models.user import User

router = APIRouter(prefix="/api/v1/ai-config/debug", tags=["Debug"])


@router.get("/db-test")
async def test_db_connection(db: AsyncSession = Depends(get_async_db)):
    """Test basic database connection."""
    try:
        result = await db.execute(text("SELECT 1"))
        return {"status": "ok", "db_connected": True, "result": result.scalar()}
    except Exception as e:
        return {"status": "error", "db_connected": False, "error": str(e)}


@router.get("/auth-test")
async def test_auth(current_user: User = Depends(CurrentUserRequired)):
    """Test authentication dependency."""
    return {
        "status": "ok",
        "authenticated": True,
        "user_id": current_user.id,
        "username": current_user.username,
    }


@router.get("/combined-test")
async def test_combined(
    current_user: User = Depends(CurrentUserRequired),
    db: AsyncSession = Depends(get_async_db),
):
    """Test both auth and database dependencies together."""
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()
        return {
            "status": "ok",
            "authenticated": True,
            "user_id": current_user.id,
            "username": current_user.username,
            "total_users": user_count,
        }
    except Exception as e:
        return {
            "status": "error",
            "authenticated": True,
            "user_id": current_user.id,
            "error": str(e),
        }
