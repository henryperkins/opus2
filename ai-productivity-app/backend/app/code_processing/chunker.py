# backend/app/code_processing/chunker.py
"""Semantic-aware chunking utilities used by the code-processing pipeline.

This module optionally relies on the *tiktoken* package for accurate token
counting that matches the OpenAI models.  Because *tiktoken* ships binary
extensions it is not always available in the execution environment (for
instance during CI or in minimal containers).  Import errors should therefore
not crash the whole application – we can still operate with a heuristic token
estimator.
"""

# Note: *Any* is intentionally not imported to avoid an unused import warning.
from typing import List, Dict, Optional

# The import is optional – fall back to *None* when the package is absent so
# that the rest of the application can continue to work.
try:
    import tiktoken  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – environment-specific
    tiktoken = None  # type: ignore
import logging

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Create semantic chunks from parsed code for embedding generation."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoder = None
        self._init_encoder()

    def _init_encoder(self):
        """Initialize tiktoken encoder."""
        if tiktoken is None:
            # The optional dependency is missing – use heuristic counting.
            logger.warning("tiktoken is not installed; falling back to rough character-based token estimation.")
            self.encoder = None
            return

        try:
            self.encoder = tiktoken.encoding_for_model("text-embedding-3-small")
        except Exception as exc:  # pragma: no cover – network / install issues
            # If the specific model encoding isn't available (very old tiktoken
            # version or other runtime error) we still attempt to get a
            # generic encoding.  As an ultimate fallback we disable accurate
            # token counting altogether.
            logger.warning("Unable to load tiktoken encoder – falling back to heuristic (%s)", exc)
            try:
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self.encoder = None

    def create_chunks(
        self,
        content: str,
        symbols: List[Dict],
        language: str,
        file_path: str = ""
    ) -> List[Dict]:
        """Create semantic chunks based on code structure."""
        chunks = []
        lines = content.split('\n')

        # First, create chunks for each symbol
        for symbol in symbols:
            chunk = self._create_symbol_chunk(lines, symbol, file_path, language)
            if chunk:
                chunks.append(chunk)

        # Add file header chunk if it contains imports or module docstring
        header_chunk = self._create_header_chunk(lines, symbols, file_path, language)
        if header_chunk:
            chunks.insert(0, header_chunk)

        # Handle orphaned code (code not in any symbol)
        orphan_chunks = self._create_orphan_chunks(lines, symbols, file_path, language)
        chunks.extend(orphan_chunks)

        return chunks

    def _create_symbol_chunk(
        self,
        lines: List[str],
        symbol: Dict,
        file_path: str,
        language: str
    ) -> Optional[Dict]:
        """Create a chunk for a specific symbol."""
        start_line = symbol['start_line']
        end_line = symbol['end_line'] + 1

        # Extract symbol lines
        symbol_lines = lines[start_line:end_line]
        chunk_content = '\n'.join(symbol_lines)

        # Check token count
        if self.encoder:
            tokens = len(self.encoder.encode(chunk_content))
        else:
            # Rough estimate: 4 chars per token
            tokens = len(chunk_content) // 4

        # If too large, split into smaller chunks
        if tokens > self.max_tokens:
            return self._split_large_symbol(lines, symbol, file_path, language)

        return {
            'content': chunk_content,
            'symbol_name': symbol['name'],
            'symbol_type': symbol['type'],
            'start_line': start_line,
            'end_line': end_line - 1,
            'tokens': tokens,
            'file_path': file_path,
            'language': language,
            'chunk_type': 'symbol'
        }

    def _split_large_symbol(
        self,
        lines: List[str],
        symbol: Dict,
        file_path: str,
        language: str
    ) -> Dict:
        """Split large symbols into smaller chunks."""
        # For now, just truncate - could be improved with better splitting
        start_line = symbol['start_line']
        end_line = symbol['end_line'] + 1

        # Take first N lines that fit in token limit
        chunk_lines = []
        current_tokens = 0

        for i in range(start_line, end_line):
            line = lines[i] if i < len(lines) else ""
            line_tokens = len(self.encoder.encode(line)) if self.encoder else len(line) // 4

            if current_tokens + line_tokens > self.max_tokens and chunk_lines:
                break

            chunk_lines.append(line)
            current_tokens += line_tokens

        return {
            'content': '\n'.join(chunk_lines),
            'symbol_name': symbol['name'],
            'symbol_type': symbol['type'],
            'start_line': start_line,
            'end_line': start_line + len(chunk_lines) - 1,
            'tokens': current_tokens,
            'file_path': file_path,
            'language': language,
            'chunk_type': 'symbol_partial'
        }

    def _create_header_chunk(
        self,
        lines: List[str],
        symbols: List[Dict],
        file_path: str,
        language: str
    ) -> Optional[Dict]:
        """Create chunk for file header (imports, module docstring)."""
        if not symbols:
            # No symbols, whole file might be header
            first_lines = lines[:20]  # First 20 lines
            content = '\n'.join(first_lines)

            if self.encoder:
                tokens = len(self.encoder.encode(content))
            else:
                tokens = len(content) // 4

            if tokens > 10:  # Only if substantial
                return {
                    'content': content,
                    'symbol_name': '__file_header__',
                    'symbol_type': 'header',
                    'start_line': 0,
                    'end_line': len(first_lines) - 1,
                    'tokens': tokens,
                    'file_path': file_path,
                    'language': language,
                    'chunk_type': 'header'
                }
            return None

        # Find first symbol
        first_symbol_line = min(s['start_line'] for s in symbols)

        if first_symbol_line > 0:
            header_lines = lines[:first_symbol_line]
            header_content = '\n'.join(header_lines)

            # Skip if just whitespace
            if not header_content.strip():
                return None

            if self.encoder:
                tokens = len(self.encoder.encode(header_content))
            else:
                tokens = len(header_content) // 4

            return {
                'content': header_content,
                'symbol_name': '__file_header__',
                'symbol_type': 'header',
                'start_line': 0,
                'end_line': first_symbol_line - 1,
                'tokens': tokens,
                'file_path': file_path,
                'language': language,
                'chunk_type': 'header'
            }

        return None

    def _create_orphan_chunks(
        self,
        lines: List[str],
        symbols: List[Dict],
        file_path: str,
        language: str
    ) -> List[Dict]:
        """Create chunks for code not contained in any symbol."""
        chunks = []

        # Sort symbols by start line
        sorted_symbols = sorted(symbols, key=lambda s: s['start_line'])

        # Check gaps between symbols
        for i in range(len(sorted_symbols) - 1):
            current_end = sorted_symbols[i]['end_line']
            next_start = sorted_symbols[i + 1]['start_line']

            if next_start - current_end > 2:  # More than just whitespace
                gap_lines = lines[current_end + 1:next_start]
                gap_content = '\n'.join(gap_lines)

                if gap_content.strip():  # Has actual content
                    if self.encoder:
                        tokens = len(self.encoder.encode(gap_content))
                    else:
                        tokens = len(gap_content) // 4

                    chunks.append({
                        'content': gap_content,
                        'symbol_name': f'__orphan_{i}__',
                        'symbol_type': 'orphan',
                        'start_line': current_end + 1,
                        'end_line': next_start - 1,
                        'tokens': tokens,
                        'file_path': file_path,
                        'language': language,
                        'chunk_type': 'orphan'
                    })

        # Check after last symbol
        if sorted_symbols:
            last_symbol_end = sorted_symbols[-1]['end_line']
            if last_symbol_end < len(lines) - 1:
                tail_lines = lines[last_symbol_end + 1:]
                tail_content = '\n'.join(tail_lines)

                if tail_content.strip():
                    if self.encoder:
                        tokens = len(self.encoder.encode(tail_content))
                    else:
                        tokens = len(tail_content) // 4

                    chunks.append({
                        'content': tail_content,
                        'symbol_name': '__file_tail__',
                        'symbol_type': 'tail',
                        'start_line': last_symbol_end + 1,
                        'end_line': len(lines) - 1,
                        'tokens': tokens,
                        'file_path': file_path,
                        'language': language,
                        'chunk_type': 'tail'
                    })

        return chunks

