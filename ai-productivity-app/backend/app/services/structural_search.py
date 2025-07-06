# backend/app/services/structural_search.py
"""Code structure and symbol search."""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
import re
import logging

from app.models.code import CodeDocument, CodeEmbedding

logger = logging.getLogger(__name__)


class StructuralSearch:
    """Search for code symbols and structures."""

    def __init__(self, db: Session):
        self.db = db
        self.patterns = {
            "func": re.compile(r"^func(?:tion)?:(.+)$", re.I),
            "class": re.compile(r"^class:(.+)$", re.I),
            "method": re.compile(r"^method:(.+)$", re.I),
            "interface": re.compile(r"^interface:(.+)$", re.I),
            "type": re.compile(r"^type:(.+)$", re.I),
            "import": re.compile(r"^import:(.+)$", re.I),
            "commit": re.compile(r"^commit:(.+)$", re.I),
            "blame": re.compile(r"^blame:(.+):(\d+)$", re.I),
            "doc": re.compile(r"^doc:(.+)$", re.I),
            "lint": re.compile(r"^lint:(.+)$", re.I),
            "file": re.compile(r"^file:(.+)$", re.I),
            "line": re.compile(r"^(.+):(\d+)$"),
        }

    async def search(
        self,
        query: str,
        project_ids: List[int],
        filters: Optional[Dict] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Search for code structures."""
        results = []

        # Parse query
        parsed = self._parse_query(query)
        if not parsed:
            return results

        search_type = parsed["type"]
        search_term = parsed["term"]

        if search_type == "symbol":
            results = await self._search_symbols(
                search_term, parsed.get("symbol_type"), project_ids, filters, limit
            )
        elif search_type == "file":
            results = await self._search_files(search_term, project_ids, filters, limit)
        elif search_type == "line":
            results = await self._search_line(
                parsed["file"], parsed["line"], project_ids, limit
            )
        elif search_type == "import":
            results = await self._search_imports(
                search_term, project_ids, filters, limit
            )

        return results

    def _parse_query(self, query: str) -> Optional[Dict]:
        """Parse structural query."""
        query = query.strip()

        # Check each pattern
        for pattern_name, pattern in self.patterns.items():
            match = pattern.match(query)
            if match:
                if pattern_name == "line":
                    return {
                        "type": "line",
                        "file": match.group(1),
                        "line": int(match.group(2)),
                    }
                elif pattern_name == "blame":
                    return {
                        "type": "blame",
                        "file": match.group(1).strip(),
                        "line": int(match.group(2))
                    }
                elif pattern_name == "commit":
                    return {"type": "commit", "term": match.group(1).strip()}
                elif pattern_name == "doc":
                    return {"type": "doc", "term": match.group(1).strip()}
                elif pattern_name == "lint":
                    return {"type": "lint", "term": match.group(1).strip()}
                elif pattern_name in ["func", "class", "method", "interface", "type"]:
                    return {
                        "type": "symbol",
                        "symbol_type": (
                            pattern_name if pattern_name != "func" else "function"
                        ),
                        "term": match.group(1).strip(),
                    }
                else:
                    return {"type": pattern_name, "term": match.group(1).strip()}

        # Check if it looks like a symbol name
        if re.match(r"^[A-Z]\w*$", query):  # CapitalCase
            return {"type": "symbol", "term": query}
        elif re.match(r"^[a-z]+_\w+$", query):  # snake_case
            return {"type": "symbol", "term": query}
        elif re.match(r"^[a-z]+[A-Z]\w*$", query):  # camelCase
            return {"type": "symbol", "term": query}

        return None

    async def _search_symbols(
        self,
        term: str,
        symbol_type: Optional[str],
        project_ids: List[int],
        filters: Optional[Dict],
        limit: int,
    ) -> List[Dict]:
        """Search for code symbols."""
        stmt = (
            select(CodeEmbedding)
            .join(CodeDocument)
            .where(
                CodeDocument.project_id.in_(project_ids),
                CodeEmbedding.symbol_name.ilike(f"%{term}%"),
            )
        )

        if symbol_type:
            stmt = stmt.where(CodeEmbedding.symbol_type == symbol_type)

        if filters and filters.get("language"):
            stmt = stmt.where(CodeDocument.language == filters["language"])

        stmt = stmt.limit(limit)

        results = []
        for chunk in self.db.execute(stmt).scalars():
            # Calculate relevance
            score = 0.7
            if chunk.symbol_name.lower() == term.lower():
                score = 1.0
            elif chunk.symbol_name.lower().startswith(term.lower()):
                score = 0.9

            results.append(
                {
                    "type": "structural_symbol",
                    "score": score,
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "content": chunk.chunk_content,
                    "metadata": {
                        "symbol_name": chunk.symbol_name,
                        "symbol_type": chunk.symbol_type,
                        "file_path": chunk.document.file_path,
                        "language": chunk.document.language,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                    },
                }
            )

        return sorted(results, key=lambda x: x["score"], reverse=True)

    async def _search_files(
        self, term: str, project_ids: List[int], filters: Optional[Dict], limit: int
    ) -> List[Dict]:
        """Search for files."""
        stmt = select(CodeDocument).where(
            CodeDocument.project_id.in_(project_ids),
            CodeDocument.file_path.ilike(f"%{term}%"),
        )

        if filters and filters.get("language"):
            stmt = stmt.where(CodeDocument.language == filters["language"])

        stmt = stmt.limit(limit)

        results = []
        for doc in self.db.execute(stmt).scalars():
            # Get first chunk as preview
            first_chunk = (
                self.db.query(CodeEmbedding)
                .filter_by(document_id=doc.id)
                .order_by(CodeEmbedding.start_line)
                .first()
            )

            score = 0.8
            if doc.file_path.lower().endswith(f"/{term.lower()}"):
                score = 1.0

            results.append(
                {
                    "type": "structural_file",
                    "score": score,
                    "document_id": doc.id,
                    "content": first_chunk.chunk_content if first_chunk else "",
                    "metadata": {
                        "file_path": doc.file_path,
                        "language": doc.language,
                        "file_size": doc.file_size,
                    },
                }
            )

        return sorted(results, key=lambda x: x["score"], reverse=True)

    async def _search_line(
        self, file_path: str, line_number: int, project_ids: List[int], limit: int
    ) -> List[Dict]:
        """Search for specific line in file."""
        # Find document
        doc = (
            self.db.query(CodeDocument)
            .filter(
                CodeDocument.project_id.in_(project_ids),
                CodeDocument.file_path.like(f"%{file_path}%"),
            )
            .first()
        )

        if not doc:
            return []

        # Find chunk containing line
        chunk = (
            self.db.query(CodeEmbedding)
            .filter(
                CodeEmbedding.document_id == doc.id,
                CodeEmbedding.start_line <= line_number,
                CodeEmbedding.end_line >= line_number,
            )
            .first()
        )

        if not chunk:
            return []

        return [
            {
                "type": "structural_line",
                "score": 1.0,
                "document_id": doc.id,
                "chunk_id": chunk.id,
                "content": chunk.chunk_content,
                "metadata": {
                    "file_path": doc.file_path,
                    "language": doc.language,
                    "target_line": line_number,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                },
            }
        ]

    async def _search_imports(
        self, term: str, project_ids: List[int], filters: Optional[Dict], limit: int
    ) -> List[Dict]:
        """Search for import statements."""
        stmt = select(CodeDocument).where(
            CodeDocument.project_id.in_(project_ids),
            CodeDocument.imports.like(f'%"{term}"%'),
        )

        if filters and filters.get("language"):
            stmt = stmt.where(CodeDocument.language == filters["language"])

        stmt = stmt.limit(limit)

        results = []
        for doc in self.db.execute(stmt).scalars():
            # Find import in document
            imports = doc.imports or []
            matching_imports = [
                imp for imp in imports if term.lower() in imp.get("module", "").lower()
            ]

            if matching_imports:
                # Get header chunk
                header_chunk = (
                    self.db.query(CodeEmbedding)
                    .filter_by(document_id=doc.id, symbol_type="header")
                    .first()
                )

                results.append(
                    {
                        "type": "structural_import",
                        "score": 0.9,
                        "document_id": doc.id,
                        "content": header_chunk.chunk_content if header_chunk else "",
                        "metadata": {
                            "file_path": doc.file_path,
                            "language": doc.language,
                            "imports": matching_imports,
                        },
                    }
                )

        return results
