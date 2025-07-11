# backend/app/routers/rendering_router.py
"""Rendering API router - format detection, rendering, and interactive
helpers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..services.rendering_service import RenderingServiceClient  # new import
from ..schemas.rendering import (
    ActionBindingRequest,
    ChunkRenderRequest,
    ContentValidationRequest,
    DiagramRenderRequest,
    FormatDetectionResult,
    InteractiveElement,
    InteractiveInjectionRequest,
    MathRenderRequest,
    RenderingCapabilities,
    RenderingResponse,
    ValidationResult,
)

router = APIRouter(prefix="/api/v1/rendering", tags=["rendering"])

# --------------------------------------------------------------------------- #
# Shared rendering-service dependency
# --------------------------------------------------------------------------- #


def get_renderer() -> RenderingServiceClient:
    """Return the shared RenderingServiceClient singleton (cheap call)."""
    return RenderingServiceClient(settings.render_service_url)


# --------------------------------------------------------------------------- #
# Pre-compiled regexes for format detection
# --------------------------------------------------------------------------- #
_RE_CODE = re.compile(r"```|`[^`]+`")
_RE_MATH = re.compile(r"\$.*?\$|\\\(.*?\\\)")
_RE_DIAGRAM = re.compile(r"\b(?:mermaid|graph|flowchart)\b", re.I)
_RE_TABLE = re.compile(r"\|.*\|")
_RE_INTERACTIVE = re.compile(r"\[(?:interactive|button)]", re.I)


@router.post("/detect-formats", response_model=RenderingResponse)
async def detect_formats(content: str) -> RenderingResponse:
    """
    Detect whether the chunk contains code, math, diagrams, tables, or interactive markup.
    """
    try:
        has_code = bool(_RE_CODE.search(content))
        has_math = bool(_RE_MATH.search(content))
        has_diagrams = bool(_RE_DIAGRAM.search(content))
        has_tables = bool(_RE_TABLE.search(content))
        has_interactive = bool(_RE_INTERACTIVE.search(content))

        languages: List[str] = []
        for lang in ("python", "javascript", "sql"):
            if f"```{lang}" in content:
                languages.append(lang)

        if has_code:
            primary = "code"
        elif has_math:
            primary = "math"
        elif has_diagrams:
            primary = "diagram"
        elif has_tables:
            primary = "table"
        else:
            primary = "text"

        result = FormatDetectionResult(
            has_code=has_code,
            has_math=has_math,
            has_diagrams=has_diagrams,
            has_tables=has_tables,
            has_interactive=has_interactive,
            primary_format=primary,
            detected_languages=languages or None,
            confidence=0.9,
        )
        return RenderingResponse(success=True, data=result.dict())
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"Format detection failed: {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Render chunk
# --------------------------------------------------------------------------- #
@router.post("/render-chunk", response_model=RenderingResponse)
async def render_chunk(
    request: ChunkRenderRequest,
    renderer: RenderingServiceClient = Depends(get_renderer),
) -> RenderingResponse:
    """Render a single chunk of content based on detected format."""
    try:
        start = datetime.utcnow()

        if request.format_info and request.format_info.has_code:
            # Prefer explicit code renderer when the chunk was fenced
            lang = (
                request.format_info.detected_languages[0]
                if request.format_info.detected_languages
                else "text"
            )
            rendered = await renderer.render_code(
                code=request.chunk,
                language=lang,
                theme=request.syntax_theme or "github",
            )
        else:
            has_math = request.format_info.has_math if request.format_info else False
            rendered = await renderer.render_markdown(
                content=request.chunk,
                options={
                    "syntax_theme": request.syntax_theme,
                    "enable_tables": True,
                    "enable_math": has_math,
                },
            )

        render_time = (datetime.utcnow() - start).total_seconds()
        data = {
            "content": rendered["html"],
            "formatted": True,
            "render_time": render_time,
            "format_used": (
                request.format_info.primary_format if request.format_info else "text"
            ),
            "metadata": {
                "theme": request.syntax_theme,
                "fallback": rendered.get("fallback", False),
            },
        }
        return RenderingResponse(success=True, data=data)
    except ValueError as exc:  # pragma: no cover
        # Safe fallback: return unformatted chunk.
        return RenderingResponse(
            success=False,
            data={"content": request.chunk, "formatted": False, "error": str(exc)},
        )


# --------------------------------------------------------------------------- #
# Inject interactive elements
# --------------------------------------------------------------------------- #
@router.post("/inject-interactive", response_model=RenderingResponse)
async def inject_interactive_elements(
    request: InteractiveInjectionRequest,
) -> RenderingResponse:
    """Add copy / run buttons, etc., to rendered chunks (mock)."""
    try:
        enhanced = []
        for idx, chunk in enumerate(request.chunks):
            interactives: List[InteractiveElement] = []

            if request.format_info and request.format_info.has_code:
                interactives.append(
                    InteractiveElement(
                        id=f"code_{idx}",
                        type="code",
                        content=chunk.content,
                        actions=["copy", "run", "edit"],
                        metadata={"language": "python"},
                    )
                )

            if request.format_info and request.format_info.has_interactive:
                interactives.append(
                    InteractiveElement(
                        id=f"interactive_{idx}",
                        type="button",
                        content="Click me",
                        actions=["click"],
                        metadata={"style": "primary"},
                    )
                )

            chunk.interactive_elements = interactives
            enhanced.append(chunk)

        return RenderingResponse(
            success=True,
            data={"enhanced_chunks": [c.dict() for c in enhanced]},
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"Interactive injection failed: {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Bind actions (mock)
# --------------------------------------------------------------------------- #
@router.post("/bind-actions", response_model=RenderingResponse)
async def bind_actions(request: ActionBindingRequest) -> RenderingResponse:
    """Bind actions to interactive elements."""
    try:
        bound = []
        for elem in request.elements:
            handlers = {act: f"handle{act.capitalize()}" for act in elem.actions}
            elem.metadata = {**(elem.metadata or {}), "handlers": handlers}
            bound.append(elem)
        return RenderingResponse(
            success=True, data={"bound_elements": [e.dict() for e in bound]}
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"Action binding failed: {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Math & diagram renderers (mock; peg future real client)
# --------------------------------------------------------------------------- #
@router.post("/math", response_model=RenderingResponse)
async def render_math(request: MathRenderRequest) -> RenderingResponse:
    """Render mathematical expressions."""
    html = f'<span class="math-{request.renderer}">{request.expression}</span>'
    return RenderingResponse(
        success=True, data={"html": html, "renderer": request.renderer}
    )


@router.post("/diagram", response_model=RenderingResponse)
async def render_diagram(request: DiagramRenderRequest) -> RenderingResponse:
    """Render diagrams."""
    svg = f"<svg><!-- {request.type} diagram --></svg>"
    return RenderingResponse(success=True, data={"svg": svg, "type": request.type})


# --------------------------------------------------------------------------- #
# Capabilities
# --------------------------------------------------------------------------- #
@router.get("/capabilities", response_model=RenderingResponse)
async def get_capabilities() -> RenderingResponse:
    """Get rendering capabilities."""
    caps = RenderingCapabilities(
        supported_formats=["markdown", "html", "text", "code", "math"],
        syntax_themes=["github", "monokai", "solarized", "vs-dark"],
        math_renderers=["katex", "mathjax"],
        diagram_types=["mermaid", "d3", "graphviz"],
        interactive_types=["code", "button", "form", "chart", "decision_tree"],
        max_content_length=50_000,
    )
    return RenderingResponse(success=True, data=caps.dict())


# --------------------------------------------------------------------------- #
# Content validation (simple heuristics)
# --------------------------------------------------------------------------- #
@router.post("/validate", response_model=RenderingResponse)
async def validate_content(request: ContentValidationRequest) -> RenderingResponse:
    """Validate content for safety."""
    lc = request.content.lower()
    issues = ["Script tag detected"] if "<script" in lc else []
    warns = ["`javascript:` URI detected"] if "javascript:" in lc else []
    result = ValidationResult(
        is_safe=not issues,
        issues=issues or None,
        sanitized_content=request.content,
        warnings=warns or None,
    )
    return RenderingResponse(success=True, data=result.dict())
