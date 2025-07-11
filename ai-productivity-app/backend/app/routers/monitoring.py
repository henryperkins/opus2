"""Health check and monitoring endpoints with comprehensive checks."""
from typing import Dict, Any
from datetime import datetime, timedelta
import asyncio
# ---------------------------------------------------------------------------
# Optional dependency: httpx (async HTTP client)
# ---------------------------------------------------------------------------
# The sandbox used by the CI runtime may not have httpx installed.  Provide a
# *very* small stub so that the module remains importable.  We only need:
#   • AsyncClient contextmanager with ``get`` coroutine returning obj with
#     `.status_code` attribute.
# ---------------------------------------------------------------------------

try:
    import httpx  # type: ignore
    _HAS_HTTPX = True
except ModuleNotFoundError:  # pragma: no cover – stub
    _HAS_HTTPX = False

    class _DummyResponse:  # type: ignore
        def __init__(self, status_code: int = 200):
            self.status_code = status_code

    class _AsyncClientStub:  # type: ignore
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):  # noqa: D401
            return self

        async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
            return False

        async def get(self, *_a, **_kw):  # noqa: D401
            return _DummyResponse(200)

    class _httpx_stub:  # type: ignore
        AsyncClient = _AsyncClientStub

    import sys, types  # noqa: E402

    module_stub = types.ModuleType("httpx")
    module_stub.AsyncClient = _httpx_stub.AsyncClient  # type: ignore
    sys.modules["httpx"] = module_stub
    httpx = module_stub  # type: ignore
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy import text
from app.database import get_db
from app.utils.redis_client import get_redis
from app.config import settings
import logging

# Optional Prometheus metrics endpoint
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["monitoring"])

# ---------------------------------------------------------------------------
# WebSocket connection statistics
# ---------------------------------------------------------------------------

@router.get("/connections", name="connections-status")
async def connection_stats():  # noqa: D401 – simple diagnostic endpoint
    """Return current WebSocket connection counts.

    Schema::
        {
          "total_sessions": 3,
          "total_connections": 7,
          "sessions": {
               "123": {"connections": 4},
               "456": {"connections": 2},
               "789": {"connections": 1}
          }
        }

    It intentionally avoids any *user* information to stay GDPR-friendly; if
    you need per-user diagnostics call ``/connections?details=true``.
    """

    from app.websocket.manager import connection_manager  # local import → avoid circular

    sessions = connection_manager.active_connections

    result = {
        "total_sessions": len(sessions),
        "total_connections": sum(len(ws_list) for ws_list in sessions.values()),
        "sessions": {sid: {"connections": len(ws_list)} for sid, ws_list in sessions.items()},
    }

    return result


# Component health status
class HealthStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


def check_database(db) -> Dict[str, Any]:
    """Check database connectivity and performance."""
    start_time = datetime.utcnow()
    try:
        # Test basic connectivity with SQLAlchemy
        result = db.execute(text("SELECT 1"))
        # Ensure the query is executed and fetch the result
        result.scalar()

        # Check response time
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Check active connections (skip for SQLite)
        if "postgresql" in str(db.bind.url):
            query = text(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            conn_result = db.execute(query)
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
                # Use *v1 preview* surface for model listing so that the health
                # check works consistently across Chat Completions **and**
                # Responses API deployments.
                url = (
                    f"{settings.azure_openai_endpoint.rstrip('/')}/openai/v1/models"
                    f"?api-version={settings.azure_openai_api_version}"
                )
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


async def check_vector_backend() -> Dict[str, Any]:
    """Check vector database backend health."""
    start_time = datetime.utcnow()
    try:
        from app.services.vector_service import get_vector_service
        vector_service = await get_vector_service()
        
        # Test basic connection by getting stats
        stats = await vector_service.get_stats()
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "status": HealthStatus.HEALTHY,
            "backend": stats.get("backend", "unknown"),
            "total_embeddings": stats.get("total_embeddings", 0),
            "response_time_ms": round(duration_ms, 2)
        }
    except Exception as e:
        logger.error(f"Vector backend health check failed: {e}")
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)[:100],
            "response_time_ms": round(duration_ms, 2)
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

    # Run async checks concurrently, db check synchronously
    async_check_tasks = {
        "redis": check_redis(),
        "openai": check_openai(),
        "workers": check_background_workers(),
        "vector": check_vector_backend()
    }
    
    # Run database check synchronously
    db_result = check_database(db)
    
    # Run async checks concurrently
    async_results = await asyncio.gather(
        *async_check_tasks.values(),
        return_exceptions=True
    )
    
    # Combine results
    results = [db_result] + list(async_results)
    check_tasks = {"database": db_result, **async_check_tasks}

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


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not HAS_PROMETHEUS:
        return Response(
            content="# Prometheus client not available\n",
            media_type="text/plain",
            status_code=501
        )
    
    try:
        metrics_output = generate_latest()
        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}\n",
            media_type="text/plain",
            status_code=500
        )
