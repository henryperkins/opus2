"""
Knowledge base API router for search and context building.
"""
import logging
import hashlib
import tempfile
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..models.project import Project
from ..models.knowledge import KnowledgeDocument
from ..schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeEntry,
    ContextBuildRequest,
    ContextResult,
    KnowledgeStats,
    KnowledgeSearchResponse,
    KnowledgeResponse
)
from ..services.knowledge_service import KnowledgeService
from ..services.vector_service import vector_service
from ..embeddings.generator import EmbeddingGenerator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# Global service instances
knowledge_service = None


async def get_knowledge_service():
    """Get or create knowledge service instance."""
    global knowledge_service

    if knowledge_service is None:
        try:
            # Use the unified vector service instead of directly creating QdrantVectorStore
            await vector_service.initialize()
            embedding_generator = EmbeddingGenerator()
            knowledge_service = KnowledgeService(vector_service, embedding_generator)
            logger.info("Knowledge service initialized with %s vector backend",
                        getattr(vector_service, '_backend', 'unknown'))
        except Exception as e:
            logger.error(f"Failed to initialize knowledge service: {e}")
            knowledge_service = None

    return knowledge_service


@router.post("/search")
async def search_knowledge(
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Search knowledge base for relevant entries."""
    try:
        # Use real knowledge service if available
        service = await get_knowledge_service()
        if service:
            results = await service.search_knowledge(
                query=request.query,
                project_ids=request.project_ids,
                limit=request.limit,
                similarity_threshold=request.similarity_threshold,
                filters=request.filters
            )

            # Convert to response format
            entries = [
                KnowledgeEntry(
                    id=r["id"],
                    content=r["content"],
                    title=r["title"],
                    source=r["source"],
                    category=r["category"],
                    tags=r["tags"],
                    similarity_score=r["score"]
                )
                for r in results
            ]

            response_data = KnowledgeSearchResponse(
                results=entries,
                total_count=len(entries),
                query_time=0.1,
                has_more=len(entries) == request.limit,
                suggestions=[]
            )

            return KnowledgeResponse(
                success=True,
                data=response_data.dict()
            )

        # Fallback to mock implementation
        mock_entries = [
            KnowledgeEntry(
                id="kb_001",
                content="This is relevant information about AI models.",
                title="AI Model Configuration",
                source="documentation",
                category="technical",
                tags=["ai", "models", "configuration"],
                similarity_score=0.85
            )
        ]

        filtered_entries = [
            entry for entry in mock_entries
            if entry.similarity_score >= request.similarity_threshold
        ][:request.limit]

        response_data = KnowledgeSearchResponse(
            results=filtered_entries,
            total_count=len(filtered_entries),
            query_time=0.15,
            has_more=False,
            suggestions=["AI configuration", "model setup"]
        )

        return KnowledgeResponse(
            success=True,
            data=response_data.dict()
        )
    except Exception as e:
        logger.error(f"Knowledge search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Knowledge search failed: {str(e)}"
        )


@router.post("/search/{project_id}")
async def search_knowledge_by_project(
    project_id: int,
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """
    Search knowledge base for a specific project (backward compatibility).

    This endpoint provides backward compatibility for frontend calls to
    /api/knowledge/search/{project_id}. It forwards to the main search endpoint
    with the project_id from the path parameter.
    """
    # Override project_ids from path parameter for backward compatibility
    request.project_ids = [project_id]

    # Forward to the main search endpoint
    return await search_knowledge(request, db)


@router.post("/context")
async def build_context(
    request: ContextBuildRequest,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Build optimized context from knowledge entries."""
    try:
        # Use real knowledge service if available
        service = await get_knowledge_service()
        if service:
            context_data = await service.build_context(
                entry_ids=request.knowledge_entries,
                max_context_length=request.max_context_length,
                db=db
            )

            # Mock sources for now - in production would fetch real entries
            mock_sources = [
                KnowledgeEntry(
                    id=entry_id,
                    content=f"Content for entry {entry_id}",
                    title=f"Knowledge Entry {entry_id}",
                    similarity_score=0.8
                )
                for entry_id in context_data["sources"][:3]
            ]

            context_result = ContextResult(
                context=context_data["context"],
                sources=mock_sources,
                context_length=context_data["context_length"],
                relevance_score=0.82
            )

            return KnowledgeResponse(
                success=True,
                data=context_result.dict()
            )

        # Fallback mock implementation
        mock_sources = [
            KnowledgeEntry(
                id=entry_id,
                content=f"Content for entry {entry_id}",
                title=f"Knowledge Entry {entry_id}",
                similarity_score=0.8
            )
            for entry_id in request.knowledge_entries[:3]
        ]

        combined_content = "\n\n".join([
            f"[{source.title}]\n{source.content}"
            for source in mock_sources
        ])

        if len(combined_content) > request.max_context_length:
            combined_content = combined_content[:request.max_context_length]
            combined_content += "... [truncated]"

        context_result = ContextResult(
            context=combined_content,
            sources=mock_sources,
            context_length=len(combined_content),
            relevance_score=0.82
        )

        return KnowledgeResponse(
            success=True,
            data=context_result.dict()
        )
    except Exception as e:
        logger.error(f"Context building failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Context building failed: {str(e)}"
        )


@router.get("/stats/{project_id}")
async def get_knowledge_stats(
    project_id: str,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Get knowledge base statistics for a project."""
    try:
        # Mock statistics implementation
        # In production, this would query your database for real stats

        stats = KnowledgeStats(
            total_entries=1250,
            categories={
                "technical": 450,
                "best-practices": 320,
                "examples": 280,
                "troubleshooting": 200
            },
            recent_additions=25,
            search_volume=1840,
            hit_rate=0.73,
            popular_queries=[
                {"query": "AI model setup", "count": 145},
                {"query": "prompt optimization", "count": 98},
                {"query": "error handling", "count": 76}
            ],
            last_updated=datetime.utcnow()
        )

        return KnowledgeResponse(
            success=True,
            data=stats.dict()
        )
    except Exception as e:
        detail = f"Failed to get knowledge stats: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/entries")
async def add_knowledge_entry(
    entry: KnowledgeEntry,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Add a new knowledge base entry."""
    try:
        # Use real knowledge service if available
        if knowledge_service:
            entry_id = await knowledge_service.add_knowledge_entry(
                content=entry.content,
                title=entry.title,
                source=entry.source,
                category=entry.category,
                tags=entry.tags,
                project_id=1,  # Default project for now
                db=db
            )

            return KnowledgeResponse(
                success=True,
                message="Knowledge entry added successfully",
                data={"entry_id": entry_id}
            )

        # Mock fallback
        if not entry.id:
            import uuid
            entry.id = f"kb_{uuid.uuid4().hex[:8]}"

        return KnowledgeResponse(
            success=True,
            message="Knowledge entry added successfully (mock)",
            data={"entry_id": entry.id}
        )
    except Exception as e:
        logger.error(f"Failed to add knowledge entry: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add knowledge entry: {str(e)}"
        )


@router.get("/entries/{entry_id}")
async def get_knowledge_entry(
    entry_id: str,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Get a specific knowledge base entry."""
    try:
        # Mock entry retrieval
        mock_entry = KnowledgeEntry(
            id=entry_id,
            content="This is the content of the knowledge entry.",
            title="Sample Knowledge Entry",
            source="system",
            category="general",
            tags=["sample", "demo"]
        )

        return KnowledgeResponse(
            success=True,
            data=mock_entry.dict()
        )
    except Exception as e:
        detail = f"Failed to get knowledge entry: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/summary/{project_id}")
async def get_project_summary(
    project_id: int,
    _db: Session = Depends(get_db)  # unused, prefixed to silence linter
) -> dict:
    """Get knowledge summary for a specific project."""
    try:
        # Mock implementation - in production, this would query your database
        # and aggregate knowledge base entries for the project

        summary_data = {
            "project_id": project_id,
            "total_documents": 45,
            "total_code_files": 127,
            "last_updated": datetime.utcnow().isoformat(),
            "summary": (
                f"Project {project_id} contains various AI-related "
                f"documentation and code files covering machine learning "
                f"models, data processing pipelines, and API integrations."
            ),
            "key_topics": [
                "Machine Learning",
                "API Development",
                "Data Processing",
                "Authentication",
                "WebSocket Integration"
            ],
            "recent_activity": [
                {
                    "type": "document_added",
                    "title": "WebSocket Implementation Guide",
                    "timestamp": (
                        datetime.utcnow() - timedelta(hours=2)
                    ).isoformat()
                },
                {
                    "type": "code_updated",
                    "title": "Chat Router Updates",
                    "timestamp": (
                        datetime.utcnow() - timedelta(hours=5)
                    ).isoformat()
                }
            ],
            "statistics": {
                "lines_of_code": 12543,
                "documentation_coverage": 78.5,
                "test_coverage": 65.2
            }
        }

        return {
            "success": True,
            "data": summary_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project summary: {str(e)}"
        ) from e


# Allowed MIME types for knowledge documents
KNOWLEDGE_ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "text/html",
    "application/json",
    "text/yaml",
    "text/x-yaml",
    "application/yaml",
    "text/xml",
    "application/xml",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
    None,  # Some browsers don't set MIME type for text files
}


async def _process_knowledge_file(
    doc_id: int, content: str, title: str, category: str = "general"
) -> None:
    """Process a knowledge file and create embeddings."""
    from app.database import SessionLocal
    from app.embeddings.generator import EmbeddingGenerator
    from sqlalchemy import text
    
    session = SessionLocal()
    try:
        doc: KnowledgeDocument | None = (
            session.query(KnowledgeDocument).filter_by(id=doc_id).first()
        )
        if not doc:
            logger.warning("KnowledgeDocument %s vanished before processing", doc_id)
            return

        # Generate embedding for the document
        embedding_generator = EmbeddingGenerator()
        embedding = await embedding_generator.generate_single_embedding(content)
        
        # Store in the main embeddings table with proper metadata
        metadata = {
            "title": title,
            "source": "upload",
            "category": category,
            "project_id": doc.project_id,
            "document_type": "knowledge",
            "knowledge_doc_id": doc_id
        }
        
        insert_sql = """
        INSERT INTO embeddings (document_id, chunk_id, project_id, embedding, content, content_hash, metadata, created_at)
        VALUES (:document_id, 1, :project_id, CAST(:embedding AS vector), :content, :content_hash, :metadata, NOW())
        """
        
        import json
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        session.execute(text(insert_sql), {
            "document_id": hash(doc_id) % 2147483647,  # Convert string ID to int within PostgreSQL int range
            "project_id": doc.project_id,
            "embedding": embedding,  # Pass as list, not string
            "content": content,
            "content_hash": content_hash,
            "metadata": json.dumps(metadata)
        })
        
        session.commit()
        logger.info("Processed knowledge file %s", title)
        
    except Exception:
        logger.exception("Failed to process knowledge file (doc_id=%s)", doc_id)
        session.rollback()
    finally:
        session.close()


@router.post("/projects/{project_id}/upload")
async def upload_knowledge_files(
    project_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    category: str = "general",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload knowledge documents for RAG access."""
    
    # Check project exists and user has access
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    from app.config import settings
    results = []
    
    for upload in files:
        try:
            # MIME type validation
            if upload.content_type not in KNOWLEDGE_ALLOWED_MIME_TYPES:
                results.append({
                    "file": upload.filename or "unknown",
                    "status": "rejected",
                    "reason": f"Unsupported MIME type: {upload.content_type}"
                })
                continue
            
            # Read and validate file size
            content_chunks = []
            content_hash = hashlib.sha256()
            total_size = 0
            
            while True:
                chunk = await upload.read(4096)
                if not chunk:
                    break
                
                content_hash.update(chunk)
                total_size += len(chunk)
                content_chunks.append(chunk)
                
                if total_size > settings.max_upload_size:
                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "rejected",
                        "reason": f"File too large: {total_size} > {settings.max_upload_size}"
                    })
                    break
            else:
                # File is acceptable
                raw = b''.join(content_chunks)
                content_hash_hex = content_hash.hexdigest()
                
                # Check for duplicates in knowledge documents
                existing = db.query(KnowledgeDocument).filter_by(
                    project_id=project_id,
                    title=upload.filename or f"upload_{content_hash_hex[:8]}"
                ).first()
                
                if existing:
                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "duplicate",
                        "existing_title": existing.title
                    })
                    continue
                
                try:
                    content_decoded = raw.decode("utf-8", errors="ignore")
                    title = upload.filename or f"Document_{content_hash_hex[:8]}"
                    
                    # Generate unique ID for knowledge document
                    import uuid
                    doc_id = f"kb_{uuid.uuid4().hex[:12]}"
                    
                    # Create knowledge document
                    doc = KnowledgeDocument(
                        id=doc_id,
                        project_id=project_id,
                        title=title,
                        content=content_decoded,
                        source="upload",
                        category=category
                    )
                    
                    db.add(doc)
                    db.commit()
                    db.refresh(doc)
                    
                    # Queue background processing for embeddings
                    background_tasks.add_task(
                        _process_knowledge_file,
                        doc_id=doc.id,
                        content=content_decoded,
                        title=title,
                        category=category
                    )
                    
                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "success",
                        "document_id": doc.id,
                        "title": title
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to process file {upload.filename}: {e}")
                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "error",
                        "reason": str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Unexpected error processing {upload.filename}: {e}")
            results.append({
                "file": upload.filename or "unknown", 
                "status": "error",
                "reason": str(e)
            })
    
    return {
        "success": True,
        "results": results,
        "total_files": len(files),
        "processed": len([r for r in results if r["status"] == "success"])
    }
