"""Enhanced search API with hybrid capabilities."""

import logging

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, Depends

from app.dependencies import DatabaseDep, CurrentUserRequired, CurrentUserOptional
from app.services.vector_service import (
    get_vector_service,
    VectorService,
    vector_service,
)
from app.services.hybrid_search import HybridSearch
from app.services.embedding_service import EmbeddingService
from app.embeddings.generator import EmbeddingGenerator
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    IndexRequest,
    IndexResponse,
)
from app.models.search_history import SearchHistory
from app.models.project import Project
from app.models.code import CodeDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

# Initialize services
embedding_generator = EmbeddingGenerator()


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    vector_service: VectorService = Depends(get_vector_service),  # Keep for future use
):
    """Execute hybrid search across code and documents."""
    # Initialize hybrid search with the pgvector-only VectorService
    hybrid_search = HybridSearch(db, vector_service, embedding_generator)

    # Get user's accessible projects
    if not request.project_ids:
        # Default to user's projects
        projects = db.query(Project).filter_by(owner_id=current_user.id).all()
        request.project_ids = [p.id for p in projects]

    # ------------------------------------------------------------------
    # Convert Pydantic object to plain dict so that downstream services that
    # expect a mapping (and call .get()) continue to work and so that we can
    # store the filters JSON in the database without serialization issues.
    # ------------------------------------------------------------------

    filters_dict = (
        request.filters.model_dump(exclude_none=True) if request.filters else None
    )

    # ------------------------------------------------------------------
    # Execute search (may raise).
    # ------------------------------------------------------------------

    try:
        raw_results = await hybrid_search.search(
            query=request.query,
            project_ids=request.project_ids,
            filters=filters_dict,
            limit=request.limit,
            search_types=request.search_types,
        )
    except Exception as err:  # noqa: BLE001 – translate to HTTP 500
        logger.error("Search failed: %s", err)
        raise HTTPException(status_code=500, detail="Search failed") from err

    # Format results with required fields
    formatted_results = []
    for r in raw_results:
        # Get document information for file path and language
        document_id = r.get("document_id")
        document = None
        if document_id:
            document = db.query(CodeDocument).filter_by(id=document_id).first()

        # Extract metadata
        metadata = r.get("metadata", {})

        # Create stable ID
        result_id = (
            f"{document_id}:{r.get('chunk_id', 0)}"
            if document_id
            else f"result_{len(formatted_results)}"
        )

        formatted_result = SearchResult(
            id=result_id,
            file_path=(
                document.file_path if document else metadata.get("file_path", "unknown")
            ),
            start_line=metadata.get("start_line", 1),
            end_line=metadata.get("end_line", metadata.get("start_line", 1)),
            language=(
                document.language if document else metadata.get("language", "unknown")
            ),
            content=r["content"],
            symbol=metadata.get("symbol_name"),
            search_type=r["type"],
            score=r["score"],
            # Legacy fields for backward compatibility
            type=r["type"],
            document_id=document_id,
            chunk_id=r.get("chunk_id"),
            metadata=metadata,
        )
        formatted_results.append(formatted_result)

    # Assemble response object
    response_payload = SearchResponse(
        query=request.query,
        results=formatted_results,
        total=len(formatted_results),
        search_types=request.search_types or ["hybrid"],
    )

    # Best-effort: record search in history
    try:
        db.add(
            SearchHistory(
                user_id=current_user.id,
                query_text=request.query.strip()[:255],
                filters=filters_dict,
                project_ids=request.project_ids,
            )
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 – don't fail request
        db.rollback()
        logger.warning("Failed to persist search history: %s", exc, exc_info=False)

    return response_payload


@router.get("/suggestions")
async def get_suggestions(
    q: str = Query("", min_length=2, max_length=100),
    current_user: CurrentUserOptional = None,
    db: DatabaseDep = None,
):
    """Get search suggestions."""
    if len(q) < 2:
        return {"suggestions": []}

    # Get suggestions from structural search patterns
    suggestions = []

    # Command suggestions
    if q.startswith("/"):
        commands = ["/explain", "/generate-tests", "/summarize-pr", "/grep"]
        suggestions.extend([c for c in commands if c.startswith(q)])

    # Structural search suggestions
    elif ":" in q:
        prefix, _ = q.split(":", 1)
        if prefix in ["func", "function", "class", "method", "type", "file"]:
            suggestions.append(f"{prefix}:")

    # ------------------------------------------------------------------
    # User search-history suggestions – use the most recent 50 queries so we
    # do not hit the DB with DISTINCT which is expensive on Sqlite.  We then
    # filter + de-duplicate on the python side.
    # ------------------------------------------------------------------
    if current_user and db:
        history_rows = (
            db.query(SearchHistory.query_text)
            .filter(SearchHistory.user_id == current_user.id)
            .order_by(SearchHistory.created_at.desc())
            .limit(50)
            .all()
        )

        recent_queries = [row[0] for row in history_rows]

        for h_query in recent_queries:
            condition1 = h_query.lower().startswith(q.lower())
            condition2 = h_query not in suggestions
            if condition1 and condition2:
                suggestions.append(h_query)

    return {"suggestions": suggestions[:10]}


# ---------------------------------------------------------------------------
# Search history list (paginated)
# ---------------------------------------------------------------------------


@router.get("/history")
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUserOptional = None,
    db: DatabaseDep = None,
):
    """Return the current user's recent search history (most recent first)."""

    if not current_user:
        return {"history": []}

    rows = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(limit)
        .all()
    )

    history = [
        {
            "id": r.id,
            "query": r.query_text,
            "filters": r.filters or {},
            "project_ids": r.project_ids or [],
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]

    return {"history": history}


@router.post("/index", response_model=IndexResponse)
async def index_document(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Index or re-index document embeddings."""
    # Verify document access
    document = db.query(CodeDocument).filter_by(id=request.document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify project access
    project = db.query(Project).filter_by(id=document.project_id).first()
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Initialize embedding service with unified vector service
    await vector_service.initialize()
    embedding_service = EmbeddingService(db, vector_service, embedding_generator)

    if request.async_mode:
        # Queue for background processing
        background_tasks.add_task(embedding_service.index_document, request.document_id)

        return IndexResponse(
            status="queued",
            message="Document queued for indexing",
            document_id=request.document_id,
        )
    else:
        # Process synchronously
        result = await embedding_service.index_document(request.document_id)

        return IndexResponse(
            status=result["status"],
            message=result.get("message", "Indexing complete"),
            document_id=request.document_id,
            indexed_count=result.get("indexed", 0),
            error_count=result.get("errors", 0),
        )


@router.delete("/index/{document_id}")
async def delete_index(
    document_id: int, current_user: CurrentUserRequired, db: DatabaseDep
):
    """Delete document from index."""
    # Verify access
    document = db.query(CodeDocument).filter_by(id=document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Initialize embedding service with unified vector service
    await vector_service.initialize()
    embedding_service = EmbeddingService(db, vector_service, embedding_generator)

    # Delete embeddings
    await embedding_service.delete_document_embeddings(document_id)

    return {"status": "success", "message": "Document removed from index"}
