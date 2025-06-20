"""
Rendering API router for response processing and rendering.
"""
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.rendering import (
    FormatDetectionResult,
    ChunkRenderRequest,
    InteractiveElement,
    RenderedChunk,
    InteractiveInjectionRequest,
    ActionBindingRequest,
    MathRenderRequest,
    DiagramRenderRequest,
    ContentValidationRequest,
    ValidationResult,
    RenderingCapabilities,
    RenderingResponse
)

router = APIRouter(prefix="/api/v1/rendering", tags=["rendering"])


@router.post("/detect-formats")
async def detect_formats(
    content: str,
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Detect content formats in the response."""
    try:
        # Format detection logic
        has_code = bool(re.search(r'```|`[^`]+`', content))
        has_math = bool(re.search(r'\$.*?\$|\\\(.*?\\\)', content))
        has_diagrams = bool(re.search(r'mermaid|graph|flowchart', content))
        has_tables = bool(re.search(r'\|.*\|', content))
        has_interactive = bool(
            re.search(r'\[interactive\]|\[button\]', content)
        )

        # Detect programming languages
        languages = []
        if '```python' in content:
            languages.append('python')
        if '```javascript' in content:
            languages.append('javascript')
        if '```sql' in content:
            languages.append('sql')

        # Determine primary format
        if has_code:
            primary_format = "code"
        elif has_math:
            primary_format = "math"
        elif has_diagrams:
            primary_format = "diagram"
        elif has_tables:
            primary_format = "table"
        else:
            primary_format = "text"

        result = FormatDetectionResult(
            has_code=has_code,
            has_math=has_math,
            has_diagrams=has_diagrams,
            has_tables=has_tables,
            has_interactive=has_interactive,
            primary_format=primary_format,
            detected_languages=languages if languages else None,
            confidence=0.9
        )

        return RenderingResponse(success=True, data=result.dict())
    except Exception as e:
        detail = f"Format detection failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/render-chunk")
async def render_chunk(
    request: ChunkRenderRequest,
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Render a content chunk with appropriate formatting."""
    try:
        start_time = datetime.utcnow()

        # Mock rendering logic
        rendered_content = request.chunk

        # Apply syntax highlighting for code
        if request.format_info and request.format_info.has_code:
            # In production, this would apply actual syntax highlighting
            rendered_content = f"<pre><code>{request.chunk}</code></pre>"

        # Process math expressions
        if request.format_info and request.format_info.has_math:
            # In production, this would render with KaTeX or MathJax
            rendered_content = rendered_content.replace(
                '$', '<span class="math">$'
            ).replace('$', '$</span>')

        render_time = (datetime.utcnow() - start_time).total_seconds()

        result = RenderedChunk(
            content=rendered_content,
            formatted=True,
            render_time=render_time,
            format_used=request.format_info.primary_format if request.format_info else "text",
            metadata={"theme": request.syntax_theme}
        )

        return RenderingResponse(success=True, data=result.dict())
    except Exception as e:
        detail = f"Chunk rendering failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/inject-interactive")
async def inject_interactive_elements(
    request: InteractiveInjectionRequest,
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Inject interactive elements into rendered content."""
    try:
        enhanced_chunks = []

        for chunk in request.chunks:
            # Mock interactive element detection and injection
            interactive_elements = []

            if request.format_info.has_code:
                # Add copy/run buttons for code blocks
                interactive_elements.append(
                    InteractiveElement(
                        id=f"code_{len(enhanced_chunks)}",
                        type="code",
                        content=chunk.content,
                        actions=["copy", "run", "edit"],
                        metadata={"language": "python"}
                    )
                )

            if request.format_info.has_interactive:
                # Add custom interactive elements
                interactive_elements.append(
                    InteractiveElement(
                        id=f"interactive_{len(enhanced_chunks)}",
                        type="button",
                        content="Click me",
                        actions=["click", "hover"],
                        metadata={"style": "primary"}
                    )
                )

            # Create enhanced chunk
            enhanced_chunk = RenderedChunk(
                content=chunk.content,
                formatted=chunk.formatted,
                interactive_elements=interactive_elements,
                render_time=chunk.render_time,
                format_used=chunk.format_used,
                metadata=chunk.metadata
            )

            enhanced_chunks.append(enhanced_chunk)

        return RenderingResponse(
            success=True,
            data={"enhanced_chunks": [chunk.dict() for chunk in enhanced_chunks]}
        )
    except Exception as e:
        detail = f"Interactive element injection failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/bind-actions")
async def bind_actions(
    request: ActionBindingRequest,
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Bind actions to interactive elements."""
    try:
        bound_elements = []

        for element in request.elements:
            # Mock action binding
            action_handlers = {}

            for action in element.actions:
                if action == "copy":
                    action_handlers[action] = "handleCopy"
                elif action == "run":
                    action_handlers[action] = "handleRun"
                elif action == "edit":
                    action_handlers[action] = "handleEdit"
                elif action == "click":
                    action_handlers[action] = "handleClick"

            # Create bound element
            bound_element = InteractiveElement(
                id=element.id,
                type=element.type,
                content=element.content,
                actions=element.actions,
                metadata={
                    **(element.metadata or {}),
                    "handlers": action_handlers
                },
                position=element.position
            )

            bound_elements.append(bound_element)

        return RenderingResponse(
            success=True,
            data={"bound_elements": [elem.dict() for elem in bound_elements]}
        )
    except Exception as e:
        detail = f"Action binding failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/math")
async def render_math(
    request: MathRenderRequest,
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Render mathematical expressions."""
    try:
        # Mock math rendering
        # In production, this would use KaTeX or MathJax

        rendered_math = {
            "expression": request.expression,
            "renderer": request.renderer,
            "html": f'<span class="math-{request.renderer}">{request.expression}</span>',
            "success": True
        }

        return RenderingResponse(success=True, data=rendered_math)
    except Exception as e:
        detail = f"Math rendering failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/diagram")
async def render_diagram(
    request: DiagramRenderRequest,
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Render diagram content."""
    try:
        # Mock diagram rendering
        # In production, this would use Mermaid, D3, etc.

        rendered_diagram = {
            "code": request.code,
            "type": request.type,
            "svg": f'<svg><!-- {request.type} diagram --></svg>',
            "success": True
        }

        return RenderingResponse(success=True, data=rendered_diagram)
    except Exception as e:
        detail = f"Diagram rendering failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/capabilities")
async def get_capabilities(
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Get rendering capabilities and supported formats."""
    try:
        capabilities = RenderingCapabilities(
            supported_formats=["markdown", "html", "text", "code", "math"],
            syntax_themes=["github", "monokai", "solarized", "vs-dark"],
            math_renderers=["katex", "mathjax"],
            diagram_types=["mermaid", "d3", "graphviz"],
            interactive_types=["code", "button", "form", "chart", "decision_tree"],
            max_content_length=50000
        )

        return RenderingResponse(success=True, data=capabilities.dict())
    except Exception as e:
        detail = f"Failed to get capabilities: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/validate")
async def validate_content(
    request: ContentValidationRequest,
    db: Session = Depends(get_db)
) -> RenderingResponse:
    """Validate content for security."""
    try:
        # Mock content validation
        # In production, this would perform actual XSS and security checks

        issues = []
        warnings = []

        if "<script" in request.content.lower():
            issues.append("Script tags detected")

        if "javascript:" in request.content.lower():
            warnings.append("JavaScript protocol detected")

        result = ValidationResult(
            is_safe=len(issues) == 0,
            issues=issues if issues else None,
            sanitized_content=request.content,  # Would be sanitized in production
            warnings=warnings if warnings else None
        )

        return RenderingResponse(success=True, data=result.dict())
    except Exception as e:
        detail = f"Content validation failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)
