"""
Knowledge base API schemas for search and context building.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    """Knowledge base search request."""
    query: str = Field(..., min_length=1)
    project_ids: Optional[List[int]] = None  # Support multiple projects
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = Field(10, ge=1, le=100)
    similarity_threshold: Optional[float] = Field(0.5, ge=0, le=1)
    include_metadata: Optional[bool] = True


class KnowledgeEntry(BaseModel):
    """Knowledge base entry result."""
    id: str
    content: str
    title: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    similarity_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContextBuildRequest(BaseModel):
    """Context building request."""
    knowledge_entries: List[str]  # List of knowledge entry IDs
    query: str
    project_id: str
    max_context_length: Optional[int] = Field(4000, ge=100, le=10000)
    prioritize_recent: Optional[bool] = True


class ContextResult(BaseModel):
    """Built context result."""
    context: str
    sources: List[KnowledgeEntry]
    context_length: int
    relevance_score: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeStats(BaseModel):
    """Knowledge base statistics."""
    total_entries: int
    categories: Dict[str, int]
    recent_additions: int
    search_volume: int
    hit_rate: float
    popular_queries: List[Dict[str, Any]]
    last_updated: datetime


class KnowledgeSearchResponse(BaseModel):
    """Knowledge search response."""
    results: List[KnowledgeEntry]
    total_count: int
    query_time: float
    has_more: bool
    suggestions: Optional[List[str]] = None


class QueryAnalysisRequest(BaseModel):
    """Query analysis request."""
    query: str = Field(..., min_length=1)
    project_id: str


class QueryAnalysisResponse(BaseModel):
    """Query analysis response."""
    intent: str = Field(..., description="Detected intent (search, implement, debug, explain, etc.)")
    task_type: str = Field(..., description="Type of task (code_review, documentation, troubleshooting, etc.)")
    complexity: str = Field(..., description="Complexity level (simple, moderate, complex)")
    keywords: List[str] = Field(..., description="Extracted keywords")
    confidence: float = Field(..., ge=0, le=1, description="Analysis confidence score")
    suggested_filters: Optional[Dict[str, Any]] = None


class KnowledgeRetrievalRequest(BaseModel):
    """Knowledge retrieval request."""
    analysis: QueryAnalysisResponse
    project_id: str
    max_docs: Optional[int] = Field(5, ge=1, le=20)
    min_confidence: Optional[float] = Field(0.2, ge=0, le=1)
    auto_context: Optional[bool] = True


class ContextInjectionRequest(BaseModel):
    """Context injection request."""
    query: str = Field(..., min_length=1)
    knowledge: List[KnowledgeEntry]
    citation_style: Optional[str] = Field("inline", pattern="^(inline|footnote)$")
    max_context_length: Optional[int] = Field(2000, ge=100, le=10000)


class ContextInjectionResponse(BaseModel):
    """Context injection response."""
    contextualized_query: str
    context_length: int
    citations_added: int


class CitationRequest(BaseModel):
    """Citation addition request."""
    response: str
    knowledge: List[KnowledgeEntry]
    citation_style: Optional[str] = Field("inline", pattern="^(inline|footnote)$")


class CitationResponse(BaseModel):
    """Citation addition response."""
    response_with_citations: str
    citations: Dict[str, Any]
    citation_count: int


class KnowledgeResponse(BaseModel):
    """Standard knowledge API response."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
