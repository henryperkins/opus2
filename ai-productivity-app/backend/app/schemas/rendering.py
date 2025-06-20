"""
Rendering API schemas for response processing and rendering.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class FormatDetectionResult(BaseModel):
    """Format detection result."""
    has_code: bool = False
    has_math: bool = False
    has_diagrams: bool = False
    has_tables: bool = False
    has_interactive: bool = False
    primary_format: str = "text"
    detected_languages: Optional[List[str]] = None
    confidence: float = Field(1.0, ge=0, le=1)


class ChunkRenderRequest(BaseModel):
    """Chunk rendering request."""
    chunk: str
    format_info: Optional[FormatDetectionResult] = None
    syntax_theme: Optional[str] = "github"
    math_renderer: Optional[str] = "katex"
    diagram_renderer: Optional[str] = "mermaid"


class InteractiveElement(BaseModel):
    """Interactive element definition."""
    id: str
    type: str = Field(..., regex="^(code|decision_tree|form|button|chart)$")
    content: str
    actions: List[str]
    metadata: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, int]] = None


class RenderedChunk(BaseModel):
    """Rendered chunk result."""
    content: str
    formatted: bool = True
    interactive_elements: Optional[List[InteractiveElement]] = None
    render_time: float
    format_used: str
    metadata: Optional[Dict[str, Any]] = None


class InteractiveInjectionRequest(BaseModel):
    """Interactive elements injection request."""
    chunks: List[RenderedChunk]
    format_info: FormatDetectionResult


class ActionBindingRequest(BaseModel):
    """Action binding request."""
    elements: List[InteractiveElement]


class StreamingOptions(BaseModel):
    """Streaming configuration options."""
    chunk_size: Optional[int] = Field(5, ge=1, le=50)
    delay_ms: Optional[int] = Field(100, ge=0, le=1000)
    enable_progressive: Optional[bool] = True


class MathRenderRequest(BaseModel):
    """Math rendering request."""
    expression: str
    renderer: str = Field("katex", regex="^(katex|mathjax)$")


class DiagramRenderRequest(BaseModel):
    """Diagram rendering request."""
    code: str
    type: str = Field("mermaid", regex="^(mermaid|d3|graphviz)$")


class ContentValidationRequest(BaseModel):
    """Content validation request."""
    content: str
    check_xss: Optional[bool] = True
    check_scripts: Optional[bool] = True
    allowed_tags: Optional[List[str]] = None


class ValidationResult(BaseModel):
    """Content validation result."""
    is_safe: bool
    issues: Optional[List[str]] = None
    sanitized_content: Optional[str] = None
    warnings: Optional[List[str]] = None


class RenderingCapabilities(BaseModel):
    """Rendering capabilities and supported formats."""
    supported_formats: List[str]
    syntax_themes: List[str]
    math_renderers: List[str]
    diagram_types: List[str]
    interactive_types: List[str]
    max_content_length: int


class RenderingResponse(BaseModel):
    """Standard rendering API response."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
