# backend/app/routers/search.py
"""Enhanced search API with hybrid capabilities."""
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
import logging

from app.dependencies import DatabaseDep, CurrentUserRequired
from app.services.vector_store import VectorStore
from app.services.hybrid_search import HybridSearch
from app.services.embedding_service import EmbeddingService
from app.embeddings.generator import EmbeddingGenerator
from app.schemas.search import (
    SearchRequest, SearchResponse, SearchResult,
    IndexRequest, IndexResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

# Initialize services
vector_store = VectorStore()
embedding_generator = EmbeddingGenerator()


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Execute hybrid search across code and documents."""
    # Initialize hybrid search
    hybrid_search = HybridSearch(db, vector_store, embedding_generator)

    # Get user's accessible projects
    if not request.project_ids:
        # Default to user's projects
        from app.models.project import Project
        projects = db.query(Project).filter_by(owner_id=current_user.id).all()
        request.project_ids = [p.id for p in projects]

    # Execute search
    try:
        results = await hybrid_search.search(
            query=request.query,
            project_ids=request.project_ids,
            filters=request.filters,
            limit=request.limit,
            search_types=request.search_types
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(SearchResult(
                type=result['type'],
                score=result['score'],
                document_id=result.get('document_id'),
                chunk_id=result.get('chunk_id'),
                content=result['content'],
                metadata=result.get('metadata', {})
            ))

        return SearchResponse(
            query=request.query,
            results=formatted_results,
            total=len(formatted_results),
            search_types=request.search_types or ['hybrid']
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/suggestions")
async def get_suggestions(
    q: str = Query("", min_length=1, max_length=100),
    current_user: CurrentUserRequired = None,
    db: DatabaseDep = None
):
    """Get search suggestions."""
    if len(q) < 2:
        return {"suggestions": []}

    # Get suggestions from structural search patterns
    suggestions = []

    # Command suggestions
    if q.startswith('/'):
        commands = [
            '/explain', '/generate-tests', '/summarize-pr', '/grep'
        ]
        suggestions.extend([c for c in commands if c.startswith(q)])

    # Structural search suggestions
    elif ':' in q:
        prefix, _ = q.split(':', 1)
        if prefix in ['func', 'function', 'class', 'method', 'type', 'file']:
            suggestions.append(f"{prefix}:")

    # Symbol suggestions from recent searches
    # TODO: Implement search history tracking

    return {"suggestions": suggestions[:10]}


@router.post("/index", response_model=IndexResponse)
async def index_document(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Index or re-index document embeddings."""
    # Verify document access
    from app.models.code import CodeDocument
    document = db.query(CodeDocument).filter_by(id=request.document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify project access
    from app.models.project import Project
    project = db.query(Project).filter_by(id=document.project_id).first()
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Initialize embedding service
    embedding_service = EmbeddingService(db, vector_store, embedding_generator)

    if request.async_mode:
        # Queue for background processing
        background_tasks.add_task(
            embedding_service.index_document,
            request.document_id
        )

        return IndexResponse(
            status="queued",
            message="Document queued for indexing",
            document_id=request.document_id
        )
    else:
        # Process synchronously
        result = await embedding_service.index_document(request.document_id)

        return IndexResponse(
            status=result['status'],
            message=result.get('message', 'Indexing complete'),
            document_id=request.document_id,
            indexed_count=result.get('indexed', 0),
            error_count=result.get('errors', 0)
        )


@router.delete("/index/{document_id}")
async def delete_index(
    document_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Delete document from index."""
    # Verify access
    from app.models.code import CodeDocument
    document = db.query(CodeDocument).filter_by(id=document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Initialize embedding service
    embedding_service = EmbeddingService(db, vector_store, embedding_generator)

    # Delete embeddings
    await embedding_service.delete_document_embeddings(document_id)

    return {"status": "success", "message": "Document removed from index"}
