"""Health check and monitoring endpoints with comprehensive checks."""
from typing import Dict, Any
from datetime import datetime, timedelta
import asyncio
import httpx
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy import text
from app.database import get_db
from app.utils.redis_client import get_redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["monitoring"])


# Component health status
class HealthStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


async def check_database(db) -> Dict[str, Any]:
    """Check database connectivity and performance."""
    start_time = datetime.utcnow()
    try:
        # Test basic connectivity
        await db.execute(text("SELECT 1"))

        # Check response time
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Check active connections (skip for SQLite)
        if "postgresql" in str(db.bind.url):
            query = text(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            conn_result = await db.execute(query)
            active_connections = conn_result.scalar()
        else:
            active_connections = 1

        return {
            "status": HealthStatus.HEALTHY,
            "response_time_ms": round(duration_ms, 2),
            "active_connections": active_connections
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "response_time_ms": None
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity and performance."""
    if settings.disable_rate_limiter:
        return {
            "status": HealthStatus.HEALTHY,
            "message": "Redis check skipped (rate limiter disabled)"
        }

    start_time = datetime.utcnow()
    try:
        redis_client = await get_redis()

        # Test basic connectivity
        await redis_client.ping()

        # Check response time
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Get memory usage
        info = await redis_client.info("memory")
        memory_used_mb = info.get("used_memory", 0) / (1024 * 1024)

        return {
            "status": HealthStatus.HEALTHY,
            "response_time_ms": round(duration_ms, 2),
            "memory_used_mb": round(memory_used_mb, 2)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "response_time_ms": None
        }


async def check_openai() -> Dict[str, Any]:
    """Check OpenAI API connectivity."""
    if settings.skip_openai_health or settings.debug:
        return {
            "status": HealthStatus.HEALTHY,
            "message": "OpenAI check skipped"
        }

    start_time = datetime.utcnow()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            if settings.llm_provider == "azure":
                if not (key := settings.azure_openai_api_key):
                    return {
                        "status": HealthStatus.DEGRADED,
                        "message": "Azure key missing"
                    }
                url = (f"{settings.azure_openai_endpoint}/openai/models"
                       f"?api-version={settings.azure_openai_api_version}")
                headers = {"api-key": f"{key[:8]}..."}
            else:
                if not (key := settings.openai_api_key):
                    return {
                        "status": HealthStatus.DEGRADED,
                        "message": "OpenAI key missing"
                    }
                url = "https://api.openai.com/v1/models"
                headers = {"Authorization": f"Bearer {key[:8]}..."}

            response = await client.get(url, headers=headers)
            duration_s = (datetime.utcnow() - start_time).total_seconds()
            duration_ms = duration_s * 1000

            if response.status_code == 200:
                return {
                    "status": HealthStatus.HEALTHY,
                    "response_time_ms": round(duration_ms, 2),
                    "provider": settings.llm_provider,
                }
            return {
                "status": HealthStatus.DEGRADED,
                "response_time_ms": round(duration_ms, 2),
                "http_status": response.status_code,
            }
    except Exception as e:
        logger.error(f"OpenAI health check failed: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)[:100],
            "response_time_ms": None
        }


async def check_background_workers() -> Dict[str, Any]:
    """Check background worker health via Redis heartbeats."""
    try:
        redis_client = await get_redis()

        # Look for worker heartbeats
        worker_keys = await redis_client.keys("worker:*")
        active_workers = []
        stale_threshold = datetime.utcnow() - timedelta(seconds=45)

        for key in worker_keys:
            last_heartbeat = await redis_client.get(key)
            if last_heartbeat:
                heartbeat_time = datetime.fromisoformat(last_heartbeat)
                if heartbeat_time > stale_threshold:
                    active_workers.append(key.split(":")[-1])

        if not worker_keys:
            # No workers expected in development
            return {
                "status": HealthStatus.HEALTHY,
                "message": "No background workers configured",
                "active_workers": 0
            }
        elif len(active_workers) == 0:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "No active workers found",
                "active_workers": 0,
                "total_workers": len(worker_keys)
            }
        elif len(active_workers) < len(worker_keys):
            return {
                "status": HealthStatus.DEGRADED,
                "active_workers": len(active_workers),
                "total_workers": len(worker_keys),
                "worker_ids": active_workers
            }
        else:
            return {
                "status": HealthStatus.HEALTHY,
                "active_workers": len(active_workers),
                "worker_ids": active_workers
            }

    except Exception as e:
        logger.error(f"Worker health check failed: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "active_workers": None
        }


@router.get("/ready")
async def readiness_check(
    response: Response, db=Depends(get_db)
) -> Dict[str, Any]:
    """Comprehensive readiness check for Kubernetes."""
    checks = {}
    overall_healthy = True
    overall_status = HealthStatus.HEALTHY

    # Minimum required components
    if hasattr(settings, "health_min_components"):
        min_components = settings.health_min_components.split(",")
    else:
        min_components = ["db"]

    # Run all checks concurrently
    check_tasks = {
        "database": check_database(db),
        "redis": check_redis(),
        "openai": check_openai(),
        "workers": check_background_workers()
    }

    results = await asyncio.gather(
        *check_tasks.values(),
        return_exceptions=True
    )

    # Process results
    for (name, _), result in zip(check_tasks.items(), results):
        if isinstance(result, Exception):
            checks[name] = {
                "status": HealthStatus.UNHEALTHY,
                "error": str(result)
            }
            if name in min_components:
                overall_healthy = False
                overall_status = HealthStatus.UNHEALTHY
        else:
            checks[name] = result
            is_unhealthy = result["status"] == HealthStatus.UNHEALTHY
            if is_unhealthy and name in min_components:
                overall_healthy = False
                overall_status = HealthStatus.UNHEALTHY
            elif (result["status"] == HealthStatus.DEGRADED and
                  overall_status != HealthStatus.UNHEALTHY):
                overall_status = HealthStatus.DEGRADED

    version = (settings.app_version if hasattr(settings, "app_version")
               else "unknown")
    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": version,
    }

    # Return 503 if unhealthy
    if not overall_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return response_data


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Simple liveness check for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/startup")
async def startup_check() -> Dict[str, Any]:
    """Startup probe for Kubernetes - checks if app is ready to serve."""
    # Basic check that app has started
    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat()
    }
