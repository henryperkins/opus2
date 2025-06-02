# Multi-stage build for minimal production image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies early so that *tree_sitter* (required for the
# compilation step later) is available.
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Build and vendor the tree-sitter language bundle so that it is available at
# runtime (required by app/code_processing/parser.py).  We do this in the *build*
# stage where the compiler tool-chain is already present and then copy the
# resulting shared object into the final slim image.  Keeping the heavy build
# dependencies out of the runtime stage results in a much smaller image while
# still enabling full parsing capabilities inside the container.
# ---------------------------------------------------------------------------

# Clone the grammar repositories (shallow) and compile them into a single shared
# library at build/languages.so.  The paths must match those expected by the
# application code.
RUN mkdir -p build/tree-sitter \
    && git clone --depth 1 https://github.com/tree-sitter/tree-sitter-python      build/tree-sitter/python \
    && git clone --depth 1 https://github.com/tree-sitter/tree-sitter-javascript  build/tree-sitter/javascript \
    && git clone --depth 1 https://github.com/tree-sitter/tree-sitter-typescript  build/tree-sitter/typescript

# Attempt to compile the combined grammars into a single shared library when
# supported by the installed *tree_sitter* version. Newer releases (>0.20)
# dropped Language.build_library, so we treat compilation as an optional best-
# effort step and fall back to the stub parser when unavailable.

RUN python - <<'PY'
from pathlib import Path
try:
    from tree_sitter import Language
except ModuleNotFoundError:
    print('tree_sitter not installed – skipping grammar compilation')
    raise SystemExit(0)

GRAMMARS = [
    'build/tree-sitter/python',
    'build/tree-sitter/javascript',
    'build/tree-sitter/typescript/typescript',
    'build/tree-sitter/typescript/tsx',
]

if hasattr(Language, 'build_library'):
    out = Path('build/languages.so')
    Language.build_library(str(out), GRAMMARS)
    print('✓ tree-sitter grammars compiled →', out)
else:
    print('⚠ tree_sitter.Language.build_library missing – skipping compile')
PY

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
# Copy pre-compiled tree-sitter bundle from builder
COPY --from=builder /app/build /app/build

# Set up application directory
WORKDIR /app
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Add user bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
