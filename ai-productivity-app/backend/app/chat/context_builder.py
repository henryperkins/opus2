import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from app.models.code import CodeDocument, CodeEmbedding
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Extract and build context from chat messages."""

    # Patterns for detecting code references
    FILE_PATTERN = re.compile(r'(?:^|[\s`"])([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)(?:[:,]?\s*(?:line\s*)?(\d+))?')
    CODE_BLOCK_PATTERN = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
    SYMBOL_PATTERN = re.compile(r'(?:function|class|def|interface|type)\s+([a-zA-Z_]\w*)')

    def __init__(self, db: Session):
        self.db = db
        self.context_window = 50  # Lines around reference

    def extract_context(self, message: str, project_id: int) -> Dict:
        """Extract all context from a message."""
        context = {
            'file_references': self.extract_file_references(message),
            'code_blocks': self.extract_code_blocks(message),
            'symbols': self.extract_symbols(message),
            'chunks': []
        }

        # Get file chunks for references
        for file_ref in context['file_references']:
            chunks = self.get_file_context(
                project_id,
                file_ref['path'],
                file_ref.get('line')
            )
            context['chunks'].extend(chunks)

        # Search for symbol references
        for symbol in context['symbols']:
            chunks = self.search_symbol(project_id, symbol)
            context['chunks'].extend(chunks[:3])  # Top 3 matches

        # Deduplicate chunks
        seen = set()
        unique_chunks = []
        for chunk in context['chunks']:
            key = (chunk['document_id'], chunk['start_line'])
            if key not in seen:
                seen.add(key)
                unique_chunks.append(chunk)

        context['chunks'] = unique_chunks
        return context

    def extract_file_references(self, text: str) -> List[Dict]:
        """Extract file paths and line numbers from text."""
        references = []

        for match in self.FILE_PATTERN.finditer(text):
            file_path = match.group(1)
            line_num = match.group(2)

            # Skip common false positives
            if file_path.count('.') > 3 or file_path.startswith('http'):
                continue

            references.append({
                'path': file_path,
                'line': int(line_num) if line_num else None,
                'match': match.group(0)
            })

        return references

    def extract_code_blocks(self, text: str) -> List[Dict]:
        """Extract code blocks from markdown."""
        blocks = []

        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            code = match.group(2).strip()

            blocks.append({
                'language': language,
                'code': code,
                'length': len(code.split('\n'))
            })

        return blocks

    def extract_symbols(self, text: str) -> List[str]:
        """Extract mentioned function/class names."""
        symbols = []

        # Direct symbol mentions
        for match in self.SYMBOL_PATTERN.finditer(text):
            symbols.append(match.group(1))

        # Backtick mentions
        backtick_pattern = re.compile(r'`([a-zA-Z_]\w*)`')
        for match in backtick_pattern.finditer(text):
            name = match.group(1)
            # Heuristic: likely a symbol if mixed case or underscore
            if '_' in name or (name[0].isupper() and name[1:].islower()):
                symbols.append(name)

        return list(set(symbols))

    def get_file_context(
        self,
        project_id: int,
        file_path: str,
        line_number: Optional[int] = None
    ) -> List[Dict]:
        """Get context chunks for a file reference."""
        # Find document
        doc = self.db.query(CodeDocument).filter_by(
            project_id=project_id,
            file_path=file_path
        ).first()

        if not doc:
            # Try partial match
            doc = self.db.query(CodeDocument).filter(
                CodeDocument.project_id == project_id,
                CodeDocument.file_path.like(f'%{file_path}')
            ).first()

        if not doc:
            return []

        # Get relevant chunks
        if line_number:
            # Get chunk containing line
            chunks = self.db.query(CodeEmbedding).filter(
                CodeEmbedding.document_id == doc.id,
                CodeEmbedding.start_line <= line_number,
                CodeEmbedding.end_line >= line_number
            ).all()
        else:
            # Get first few chunks
            chunks = self.db.query(CodeEmbedding).filter_by(
                document_id=doc.id
            ).order_by(CodeEmbedding.start_line).limit(3).all()

        return [self._format_chunk(chunk) for chunk in chunks]

    def search_symbol(self, project_id: int, symbol: str) -> List[Dict]:
        """Search for symbol in project."""
        chunks = self.db.query(CodeEmbedding).join(CodeDocument).filter(
            CodeDocument.project_id == project_id,
            CodeEmbedding.symbol_name == symbol
        ).all()

        if not chunks:
            # Try partial match
            chunks = self.db.query(CodeEmbedding).join(CodeDocument).filter(
                CodeDocument.project_id == project_id,
                CodeEmbedding.symbol_name.like(f'%{symbol}%')
            ).limit(5).all()

        return [self._format_chunk(chunk) for chunk in chunks]

    def build_conversation_context(
        self,
        session_id: int,
        max_messages: int = 10
    ) -> List[Dict]:
        """Build context from recent conversation."""
        messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id,
            is_deleted=False
        ).order_by(ChatMessage.id.desc()).limit(max_messages).all()

        return [
            {
                'role': msg.role,
                'content': msg.content,
                'code_snippets': msg.code_snippets
            }
            for msg in reversed(messages)
        ]

    def _format_chunk(self, chunk: CodeEmbedding) -> Dict:
        """Format chunk for context."""
        return {
            'document_id': chunk.document_id,
            'file_path': chunk.document.file_path,
            'language': chunk.document.language,
            'symbol_name': chunk.symbol_name,
            'symbol_type': chunk.symbol_type,
            'start_line': chunk.start_line,
            'end_line': chunk.end_line,
            'content': chunk.chunk_content
        }
