# Health check endpoints for monitoring
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from datetime import datetime
from ..dependencies import DatabaseDep
from ..config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
    }


@router.get("/ready")
async def readiness_check(db: DatabaseDep, response: Response):
    """
    Readiness check including database connectivity.
    Returns 503 if any component is not ready.
    """
    checks = {"api": "ready", "timestamp": datetime.utcnow().isoformat()}

    # Check database
    try:
        db.execute(text("SELECT 1"))
        db.commit()
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Overall status
    all_ready = all(v == "ready" for k, v in checks.items() if k not in ["timestamp"])
    checks["status"] = "ready" if all_ready else "not ready"

    return checks


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}
