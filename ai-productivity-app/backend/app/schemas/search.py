# backend/app/schemas/search.py
"""Pydantic schemas for search API."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class SearchType(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    STRUCTURAL = "structural"
    HYBRID = "hybrid"


class SearchFilters(BaseModel):
    """Search filters."""

    language: Optional[str] = None
    file_type: Optional[str] = None
    symbol_type: Optional[str] = None
    tags: Optional[List[str]] = None


class SearchRequest(BaseModel):
    """Search request schema."""

    query: str = Field(..., min_length=1, max_length=500)
    project_ids: Optional[List[int]] = None
    filters: Optional[SearchFilters] = None
    limit: int = Field(20, ge=1, le=100)
    search_types: Optional[List[SearchType]] = None


class SearchResult(BaseModel):
    """Individual search result."""

    id: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    content: str
    symbol: Optional[str] = None
    search_type: str
    score: float
    # Legacy fields for backward compatibility
    type: Optional[str] = None
    document_id: Optional[int] = None
    chunk_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response schema."""

    query: str
    results: List[SearchResult]
    total: int
    search_types: List[str]


class SuggestionsResponse(BaseModel):
    """Suggestions response schema."""

    suggestions: List[str]


class IndexRequest(BaseModel):
    """Document indexing request."""

    document_id: int
    force_reindex: bool = False
    async_mode: bool = True


class IndexResponse(BaseModel):
    """Indexing response."""

    status: str
    message: str
    document_id: int
    indexed_count: Optional[int] = None
    error_count: Optional[int] = None
