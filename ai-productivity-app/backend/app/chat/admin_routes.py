# backend/app/chat/admin_routes.py
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import VectorServiceDep
from app.services.qdrant_service import QdrantService

router = APIRouter()


@router.post("/gc-qdrant", summary="Trigger Qdrant Garbage Collection")
async def trigger_qdrant_gc(vector_service: VectorServiceDep):
    """
    Triggers the garbage collection process for the Qdrant vector store
    to remove any dangling points.
    """
    if not isinstance(vector_service._backend, QdrantService):
        raise HTTPException(
            status_code=400,
            detail="Garbage collection is only available for the Qdrant vector store.",
        )

    removed_count = await vector_service._backend.gc_dangling_points()
    return {
        "message": f"Qdrant garbage collection completed. Removed {removed_count} dangling points."
    }
