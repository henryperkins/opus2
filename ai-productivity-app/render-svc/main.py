"""
External rendering microservice
FastAPI service for syntax highlighting, math, and diagram rendering
"""
import os
import html
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Try to import optional dependencies
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.formatters import HtmlFormatter
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

app = FastAPI(
    title="Rendering Service",
    description="External rendering service for syntax highlighting, math, and diagrams",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class MarkdownRequest(BaseModel):
    content: str = Field(..., description="Markdown content to render")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CodeRequest(BaseModel):
    code: str = Field(..., description="Code to highlight")
    language: str = Field(..., description="Programming language")
    theme: str = Field(default="github", description="Syntax highlighting theme")


class MathRequest(BaseModel):
    expression: str = Field(..., description="Mathematical expression")
    renderer: str = Field(default="katex", description="Math renderer to use")


class DiagramRequest(BaseModel):
    code: str = Field(..., description="Diagram code")
    type: str = Field(default="mermaid", description="Diagram type")


class RenderResponse(BaseModel):
    html: Optional[str] = None
    svg: Optional[str] = None
    format: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    renderer: Optional[str] = None
    fallback: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "render-svc",
        "capabilities": {
            "markdown": MARKDOWN_AVAILABLE,
            "syntax_highlighting": PYGMENTS_AVAILABLE,
            "math": False,  # Would be True if KaTeX/MathJax is available
            "diagrams": False  # Would be True if Mermaid is available
        },
        "timestamp": datetime.utcnow()
    }


@app.post("/render/markdown", response_model=RenderResponse)
async def render_markdown(request: MarkdownRequest):
    """Render markdown content to HTML."""
    try:
        if not MARKDOWN_AVAILABLE:
            # Fallback: escape HTML and wrap in <pre>
            escaped = html.escape(request.content)
            return RenderResponse(
                html=f"<pre>{escaped}</pre>",
                format="text",
                fallback=True
            )

        # Configure markdown extensions based on options
        extensions = ['tables', 'fenced_code']

        if request.options.get("enable_tables", True):
            if 'tables' not in extensions:
                extensions.append('tables')

        if request.options.get("enable_math", False):
            raise HTTPException(
                status_code=501,
                detail="Math rendering requested but math extension is not available in the rendering service."
            )

        if PYGMENTS_AVAILABLE and request.options.get("syntax_theme"):
            extensions.append('codehilite')

        html_content = markdown.markdown(
            request.content,
            extensions=extensions
        )

        return RenderResponse(
            html=html_content,
            format="markdown",
            fallback=False
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Markdown rendering failed: {str(e)}"
        )


@app.post("/render/code", response_model=RenderResponse)
async def render_code(request: CodeRequest):
    """Render code with syntax highlighting."""
    try:
        if not PYGMENTS_AVAILABLE:
            # Fallback: HTML escape and basic formatting
            escaped = html.escape(request.code)
            return RenderResponse(
                html=f'<pre><code class="language-{request.language}">'
                     f'{escaped}</code></pre>',
                language=request.language,
                theme=request.theme,
                fallback=True
            )

        try:
            lexer = get_lexer_by_name(request.language)
        except ClassNotFound:
            # Try to guess the lexer
            try:
                lexer = guess_lexer(request.code)
            except ClassNotFound:
                # Use plain text lexer
                lexer = get_lexer_by_name('text')

        # Configure formatter based on theme
        formatter_options = {
            'style': request.theme,
            'cssclass': f'highlight-{request.theme}',
        }

        formatter = HtmlFormatter(**formatter_options)
        highlighted = highlight(request.code, lexer, formatter)

        return RenderResponse(
            html=highlighted,
            language=request.language,
            theme=request.theme,
            fallback=False
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Code rendering failed: {str(e)}"
        )


@app.post("/render/math", response_model=RenderResponse)
async def render_math(request: MathRequest):
    """Render mathematical expressions."""
    try:
        # Fallback math rendering (would use KaTeX/MathJax in production)
        escaped = html.escape(request.expression)

        return RenderResponse(
            html=f'<span class="math-{request.renderer}" '
                 f'data-expr="{escaped}">{escaped}</span>',
            renderer=request.renderer,
            fallback=True
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Math rendering failed: {str(e)}"
        )


@app.post("/render/diagram", response_model=RenderResponse)
async def render_diagram(request: DiagramRequest):
    """Render diagrams."""
    try:
        # Fallback diagram rendering (would use Mermaid CLI in production)
        escaped_code = html.escape(request.code)

        return RenderResponse(
            svg=f'<svg viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">'
                f'<text x="10" y="20" font-family="monospace" font-size="12">'
                f'Diagram ({request.type})</text>'
                f'<text x="10" y="40" font-family="monospace" font-size="10">'
                f'Code: {escaped_code[:50]}...</text>'
                f'</svg>',
            format=request.type,
            fallback=True
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Diagram rendering failed: {str(e)}"
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
