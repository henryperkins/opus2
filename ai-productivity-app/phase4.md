# Phase 4 Implementation Plan: Code Processing & Knowledge Management

## Overview
Phase 4 implements the core code intelligence features, transforming the app into a code-aware productivity tool. This phase focuses on practical code parsing and search capabilities without over-engineering for our small team.

## Timeline: 3 Weeks (15 Business Days)

## Objectives
1. Implement code file upload and parsing with tree-sitter
2. Create semantic code chunking for embeddings
3. Add Git repository integration
4. Build vector search with SQLite VSS
5. Create dependency graph visualization

## Technical Approach
- **Parsing**: Tree-sitter for Python, JavaScript, TypeScript
- **Storage**: SQLite with JSON fields for flexibility
- **Embeddings**: OpenAI text-embedding-3-small
- **Search**: SQLite VSS extension for vector similarity
- **Git**: GitPython for repository operations

---

## Week 1: Code Parsing Infrastructure (Days 1-5)

### Day 1-2: Database Models & Tree-sitter Setup

**Tasks:**
1. Create CodeDocument and CodeEmbedding models
2. Set up tree-sitter with language grammars
3. Implement language detection
4. Create code parsing utilities

**Deliverables:**

`backend/app/models/code.py` (≤300 lines)
```python
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class CodeDocument(Base, TimestampMixin):
    __tablename__ = 'code_documents'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    file_path = Column(String(500), nullable=False)
    repo_name = Column(String(200))
    commit_sha = Column(String(40))

    # Code metadata
    language = Column(String(50))
    file_size = Column(Integer)
    last_modified = Column(DateTime)

    # Parsing results stored as JSON for flexibility
    symbols = Column(JSON)  # [{name, type, line_start, line_end}]
    imports = Column(JSON)  # List of imports/dependencies

    # Search optimization
    content_hash = Column(String(64))
    is_indexed = Column(Boolean, default=False)

    # Relationships
    project = relationship("Project", back_populates="code_documents")
    embeddings = relationship("CodeEmbedding", back_populates="document", cascade="all, delete-orphan")

class CodeEmbedding(Base, TimestampMixin):
    __tablename__ = 'code_embeddings'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('code_documents.id'), nullable=False)

    # Chunk information
    chunk_content = Column(Text, nullable=False)
    symbol_name = Column(String(200))
    symbol_type = Column(String(50))  # function, class, method, etc.
    start_line = Column(Integer)
    end_line = Column(Integer)

    # Embedding data (stored as JSON array for SQLite)
    embedding = Column(JSON)
    embedding_model = Column(String(50), default='text-embedding-3-small')

    # Relationships
    document = relationship("CodeDocument", back_populates="embeddings")
```

`backend/scripts/setup_tree_sitter.py` (≤150 lines)
```python
#!/usr/bin/env python3
"""Download and compile tree-sitter grammars"""

import os
import subprocess
from pathlib import Path

LANGUAGES = {
    'python': 'https://github.com/tree-sitter/tree-sitter-python',
    'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript',
    'typescript': 'https://github.com/tree-sitter/tree-sitter-typescript'
}

def setup_grammars():
    build_dir = Path('build/tree-sitter')
    build_dir.mkdir(parents=True, exist_ok=True)

    for lang, repo in LANGUAGES.items():
        print(f"Setting up {lang}...")
        lang_dir = build_dir / lang

        # Clone if not exists
        if not lang_dir.exists():
            subprocess.run(['git', 'clone', repo, str(lang_dir)], check=True)

        # Build grammar
        # ... compilation logic ...
```

### Day 3-4: Code Parsing Service

**Tasks:**
1. Implement tree-sitter parser wrapper
2. Create semantic chunking algorithm
3. Add symbol extraction logic
4. Build import/dependency detection

**Deliverables:**

`backend/app/code_processing/parser.py` (≤400 lines)
```python
import tree_sitter
from tree_sitter import Language, Parser
from typing import List, Dict, Any
import hashlib

class CodeParser:
    def __init__(self):
        self.parsers = {}
        self._load_languages()

    def _load_languages(self):
        """Load compiled tree-sitter languages"""
        Language.build_library(
            'build/languages.so',
            ['build/tree-sitter/python',
             'build/tree-sitter/javascript',
             'build/tree-sitter/typescript']
        )

        self.languages = {
            'python': Language('build/languages.so', 'python'),
            'javascript': Language('build/languages.so', 'javascript'),
            'typescript': Language('build/languages.so', 'typescript')
        }

    def parse_file(self, content: str, language: str) -> Dict[str, Any]:
        """Parse file and extract structured information"""
        if language not in self.parsers:
            parser = Parser()
            parser.set_language(self.languages[language])
            self.parsers[language] = parser

        tree = self.parsers[language].parse(bytes(content, "utf8"))

        return {
            'symbols': self._extract_symbols(tree, language),
            'imports': self._extract_imports(tree, language),
            'tree': tree
        }

    def _extract_symbols(self, tree, language: str) -> List[Dict]:
        """Extract functions, classes, methods"""
        symbols = []

        # Language-specific queries
        queries = {
            'python': """
                (function_definition name: (identifier) @func)
                (class_definition name: (identifier) @class)
            """,
            'javascript': """
                (function_declaration name: (identifier) @func)
                (class_declaration name: (identifier) @class)
                (method_definition name: (property_identifier) @method)
            """
        }

        query = self.languages[language].query(queries.get(language, ""))
        captures = query.captures(tree.root_node)

        for node, name in captures:
            symbols.append({
                'name': node.text.decode('utf8'),
                'type': name,
                'start_line': node.start_point[0],
                'end_line': node.end_point[0],
                'start_byte': node.start_byte,
                'end_byte': node.end_byte
            })

        return symbols
```

`backend/app/code_processing/chunker.py` (≤300 lines)
```python
from typing import List, Dict, Any
import tiktoken

class SemanticChunker:
    """Intelligent code chunking for embeddings"""

    def __init__(self, max_tokens: int = 500):
        self.max_tokens = max_tokens
        self.encoder = tiktoken.encoding_for_model("text-embedding-3-small")

    def create_chunks(self, content: str, symbols: List[Dict], language: str) -> List[Dict]:
        """Create semantic chunks based on code structure"""
        chunks = []
        lines = content.split('\n')

        # First, chunk by symbol (function/class)
        for symbol in symbols:
            start = symbol['start_line']
            end = symbol['end_line'] + 1
            chunk_lines = lines[start:end]
            chunk_content = '\n'.join(chunk_lines)

            # Check token count
            tokens = len(self.encoder.encode(chunk_content))

            if tokens <= self.max_tokens:
                chunks.append({
                    'content': chunk_content,
                    'symbol_name': symbol['name'],
                    'symbol_type': symbol['type'],
                    'start_line': start,
                    'end_line': end,
                    'tokens': tokens
                })
            else:
                # Split large symbols into smaller chunks
                sub_chunks = self._split_large_chunk(chunk_lines, symbol)
                chunks.extend(sub_chunks)

        # Add file-level chunk for imports and globals
        if symbols:
            first_symbol_line = min(s['start_line'] for s in symbols)
            if first_symbol_line > 0:
                header_content = '\n'.join(lines[:first_symbol_line])
                if header_content.strip():
                    chunks.append({
                        'content': header_content,
                        'symbol_name': '__file_header__',
                        'symbol_type': 'header',
                        'start_line': 0,
                        'end_line': first_symbol_line,
                        'tokens': len(self.encoder.encode(header_content))
                    })

        return chunks
```

### Day 5: File Upload Endpoints

**Tasks:**
1. Implement file upload API
2. Add batch processing support
3. Create background task for parsing
4. Add progress tracking

**Deliverables:**

`backend/app/routers/code.py` (≤400 lines)
```python
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from typing import List
import aiofiles
import hashlib

router = APIRouter(prefix="/api/code", tags=["code"])

@router.post("/projects/{project_id}/upload")
async def upload_files(
    project_id: int,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process code files"""
    # Verify project access
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    results = []
    for file in files:
        # Save file temporarily
        content = await file.read()
        content_hash = hashlib.sha256(content).hexdigest()

        # Check if already processed
        existing = db.query(CodeDocument).filter_by(
            project_id=project_id,
            file_path=file.filename,
            content_hash=content_hash
        ).first()

        if existing:
            results.append({"file": file.filename, "status": "already_processed"})
            continue

        # Create document record
        doc = CodeDocument(
            project_id=project_id,
            file_path=file.filename,
            file_size=len(content),
            content_hash=content_hash,
            language=detect_language(file.filename)
        )
        db.add(doc)
        db.commit()

        # Queue for processing
        background_tasks.add_task(
            process_code_file,
            doc.id,
            content.decode('utf-8'),
            doc.language
        )

        results.append({"file": file.filename, "status": "queued"})

    # Create timeline event
    create_timeline_event(
        db, project_id, "files_uploaded",
        f"Uploaded {len(files)} files",
        {"files": [f.filename for f in files]}
    )

    return {"results": results}

async def process_code_file(doc_id: int, content: str, language: str):
    """Background task to parse and chunk code"""
    async with get_async_db() as db:
        parser = CodeParser()
        chunker = SemanticChunker()

        # Parse file
        parse_result = parser.parse_file(content, language)

        # Update document with symbols
        doc = db.query(CodeDocument).filter_by(id=doc_id).first()
        doc.symbols = parse_result['symbols']
        doc.imports = parse_result['imports']
        doc.is_indexed = True

        # Create chunks
        chunks = chunker.create_chunks(content, parse_result['symbols'], language)

        # Store chunks (embeddings will be generated separately)
        for chunk in chunks:
            embedding = CodeEmbedding(
                document_id=doc_id,
                chunk_content=chunk['content'],
                symbol_name=chunk['symbol_name'],
                symbol_type=chunk['symbol_type'],
                start_line=chunk['start_line'],
                end_line=chunk['end_line']
            )
            db.add(embedding)

        db.commit()
```

---

## Week 2: Git Integration & Embeddings (Days 6-10)

### Day 6-7: Git Repository Integration

**Tasks:**
1. Implement Git clone/pull functionality
2. Add repository watching for changes
3. Create diff processing for updates
4. Build commit tracking

**Deliverables:**

`backend/app/code_processing/git_integration.py` (≤350 lines)
```python
import git
from pathlib import Path
import tempfile
from typing import List, Dict, Optional

class GitManager:
    """Manage git repository operations"""

    def __init__(self, base_path: str = "repos"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    async def clone_repository(
        self,
        repo_url: str,
        project_id: int,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Clone a repository and return file list"""
        repo_name = self._extract_repo_name(repo_url)
        repo_path = self.base_path / f"project_{project_id}" / repo_name

        # Clone or update
        if repo_path.exists():
            repo = git.Repo(repo_path)
            origin = repo.remote('origin')
            origin.pull()
        else:
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            repo = git.Repo.clone_from(repo_url, repo_path, branch=branch)

        # Get file list
        files = []
        for item in repo.tree().traverse():
            if item.type == 'blob':  # It's a file
                file_path = str(item.path)
                if self._should_process_file(file_path):
                    files.append({
                        'path': file_path,
                        'size': item.size,
                        'sha': item.binsha.hex()
                    })

        return {
            'repo_path': str(repo_path),
            'commit_sha': repo.head.commit.hexsha,
            'branch': repo.active_branch.name,
            'files': files
        }

    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed"""
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx'}
        path = Path(file_path)

        # Skip common non-code directories
        skip_dirs = {'node_modules', '.git', '__pycache__', 'dist', 'build'}
        if any(part in skip_dirs for part in path.parts):
            return False

        return path.suffix in extensions

    async def get_file_content(self, repo_path: str, file_path: str) -> str:
        """Get content of a specific file"""
        full_path = Path(repo_path) / file_path
        async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
            return await f.read()
```

`backend/app/routers/repositories.py` (≤250 lines)
```python
@router.post("/projects/{project_id}/repositories")
async def connect_repository(
    project_id: int,
    repo_url: str,
    branch: str = "main",
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect a git repository to a project"""
    project = verify_project_access(db, project_id, current_user)

    # Queue repository processing
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        process_repository,
        task_id,
        project_id,
        repo_url,
        branch
    )

    # Create timeline event
    create_timeline_event(
        db, project_id, "repository_connected",
        f"Connected repository: {repo_url}",
        {"repo_url": repo_url, "branch": branch, "task_id": task_id}
    )

    return {"task_id": task_id, "status": "processing"}

async def process_repository(task_id: str, project_id: int, repo_url: str, branch: str):
    """Background task to clone and process repository"""
    git_manager = GitManager()

    try:
        # Clone repository
        result = await git_manager.clone_repository(repo_url, project_id, branch)

        # Process each file
        async with get_async_db() as db:
            for file_info in result['files']:
                content = await git_manager.get_file_content(
                    result['repo_path'],
                    file_info['path']
                )

                # Create document
                doc = CodeDocument(
                    project_id=project_id,
                    file_path=file_info['path'],
                    repo_name=repo_url.split('/')[-1].replace('.git', ''),
                    commit_sha=result['commit_sha'],
                    file_size=file_info['size'],
                    content_hash=file_info['sha'],
                    language=detect_language(file_info['path'])
                )
                db.add(doc)
                db.commit()

                # Process file
                await process_code_file(doc.id, content, doc.language)

        # Update task status
        await update_task_status(task_id, "completed", result)

    except Exception as e:
        await update_task_status(task_id, "failed", {"error": str(e)})
```

### Day 8-9: Embedding Generation

**Tasks:**
1. Implement OpenAI embedding generation
2. Create batch processing for efficiency
3. Add embedding caching
4. Build vector storage with SQLite VSS

**Deliverables:**

`backend/app/embeddings/generator.py` (≤300 lines)
```python
import openai
from typing import List, Dict
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

class EmbeddingGenerator:
    """Generate embeddings using OpenAI API"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = openai.AsyncOpenAI()
        self.batch_size = 50  # OpenAI limit

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            response = await self.client.embeddings.create(
                model=self.model,
                input=batch
            )

            batch_embeddings = [e.embedding for e in response.data]
            embeddings.extend(batch_embeddings)

        return embeddings

    async def generate_and_store(
        self,
        chunks: List[CodeEmbedding],
        db: Session
    ):
        """Generate embeddings for code chunks and update database"""
        # Extract texts
        texts = []
        for chunk in chunks:
            # Format text with context
            text = f"{chunk.symbol_type} {chunk.symbol_name}\n{chunk.chunk_content}"
            texts.append(text)

        # Generate embeddings
        embeddings = await self.generate_embeddings(texts)

        # Update chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding  # Will be stored as JSON
            db.add(chunk)

        db.commit()
```

`backend/app/embeddings/batch_processor.py` (≤200 lines)
```python
from sqlalchemy import select
import asyncio

class BatchEmbeddingProcessor:
    """Process embeddings in batches for efficiency"""

    def __init__(self, generator: EmbeddingGenerator):
        self.generator = generator
        self.queue = asyncio.Queue()
        self.processing = False

    async def process_project_embeddings(self, project_id: int):
        """Generate all embeddings for a project"""
        async with get_async_db() as db:
            # Get all chunks without embeddings
            chunks = db.query(CodeEmbedding).join(CodeDocument).filter(
                CodeDocument.project_id == project_id,
                CodeEmbedding.embedding.is_(None)
            ).all()

            if not chunks:
                return {"status": "no_chunks_to_process"}

            # Process in batches
            total = len(chunks)
            processed = 0

            for i in range(0, total, 100):  # Process 100 at a time
                batch = chunks[i:i + 100]
                await self.generator.generate_and_store(batch, db)
                processed += len(batch)

                # Update progress
                await update_task_progress(
                    project_id,
                    "embedding_generation",
                    {"processed": processed, "total": total}
                )

            return {"processed": processed, "total": total}
```

### Day 10: Vector Store Setup

**Tasks:**
1. Set up SQLite VSS extension
2. Create vector search functionality
3. Implement similarity scoring
4. Add search result ranking

**Deliverables:**

`backend/app/search/vector_store.py` (≤400 lines)
```python
import sqlite3
import json
import numpy as np
from typing import List, Dict, Tuple

class SQLiteVectorStore:
    """Vector store using SQLite VSS extension"""

    def __init__(self, db_path: str = "data/vectors.db"):
        self.conn = sqlite3.connect(db_path)
        self._setup_vss()

    def _setup_vss(self):
        """Initialize SQLite VSS"""
        # Load VSS extension
        self.conn.enable_load_extension(True)
        self.conn.load_extension("vector0")
        self.conn.enable_load_extension(False)

        # Create tables
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vss_embeddings USING vss0(
                embedding(1536)
            );
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_metadata (
                rowid INTEGER PRIMARY KEY,
                chunk_id INTEGER,
                project_id INTEGER,
                document_id INTEGER,
                content TEXT,
                metadata JSON,
                FOREIGN KEY (chunk_id) REFERENCES code_embeddings(id)
            );
        """)

        self.conn.commit()

    def add_embeddings(self, embeddings: List[Tuple[int, List[float], Dict]]):
        """Add embeddings to the store"""
        for chunk_id, embedding, metadata in embeddings:
            # Convert to numpy array
            embedding_array = np.array(embedding, dtype=np.float32)

            # Insert into VSS table
            cursor = self.conn.execute(
                "INSERT INTO vss_embeddings(rowid, embedding) VALUES (NULL, ?)",
                (embedding_array.tobytes(),)
            )
            rowid = cursor.lastrowid

            # Insert metadata
            self.conn.execute(
                """INSERT INTO embedding_metadata
                   (rowid, chunk_id, project_id, document_id, content, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    rowid,
                    chunk_id,
                    metadata['project_id'],
                    metadata['document_id'],
                    metadata['content'],
                    json.dumps(metadata)
                )
            )

        self.conn.commit()

    def search(
        self,
        query_embedding: List[float],
        project_id: int,
        k: int = 10
    ) -> List[Dict]:
        """Search for similar embeddings"""
        query_array = np.array(query_embedding, dtype=np.float32)

        results = self.conn.execute("""
            SELECT
                m.chunk_id,
                m.content,
                m.metadata,
                vss_distance_l2(e.embedding, ?) as distance
            FROM vss_embeddings e
            JOIN embedding_metadata m ON e.rowid = m.rowid
            WHERE m.project_id = ?
                AND vss_search(e.embedding, ?)
            ORDER BY distance
            LIMIT ?
        """, (
            query_array.tobytes(),
            project_id,
            query_array.tobytes(),
            k
        )).fetchall()

        return [
            {
                'chunk_id': row[0],
                'content': row[1],
                'metadata': json.loads(row[2]),
                'score': 1 / (1 + row[3])  # Convert distance to similarity
            }
            for row in results
        ]
```

---

## Week 3: Search & Visualization (Days 11-15)

### Day 11-12: Hybrid Search Implementation

**Tasks:**
1. Implement semantic search endpoint
2. Add keyword search functionality
3. Create hybrid ranking algorithm
4. Build search filters

**Deliverables:**

`backend/app/search/hybrid.py` (≤400 lines)
```python
from typing import List, Dict, Optional
import asyncio
from sqlalchemy import or_, and_

class HybridSearch:
    """Combine semantic and keyword search"""

    def __init__(self, vector_store: SQLiteVectorStore, embedding_generator: EmbeddingGenerator):
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator

    async def search(
        self,
        query: str,
        project_id: int,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Perform hybrid search"""
        # Run searches in parallel
        semantic_task = asyncio.create_task(
            self._semantic_search(query, project_id, limit * 2)
        )
        keyword_task = asyncio.create_task(
            self._keyword_search(query, project_id, filters, limit * 2)
        )

        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )

        # Merge and rank results
        merged = self._merge_results(semantic_results, keyword_results)

        # Apply filters
        if filters:
            merged = self._apply_filters(merged, filters)

        return merged[:limit]

    async def _semantic_search(self, query: str, project_id: int, limit: int):
        """Semantic search using embeddings"""
        # Generate query embedding
        embeddings = await self.embedding_generator.generate_embeddings([query])
        query_embedding = embeddings[0]

        # Search vector store
        results = self.vector_store.search(query_embedding, project_id, limit)

        # Enhance with full document info
        async with get_async_db() as db:
            for result in results:
                chunk = db.query(CodeEmbedding).filter_by(
                    id=result['chunk_id']
                ).first()

                result['document'] = {
                    'file_path': chunk.document.file_path,
                    'language': chunk.document.language,
                    'repo_name': chunk.document.repo_name
                }
                result['search_type'] = 'semantic'

        return results

    async def _keyword_search(self, query: str, project_id: int, filters: Dict, limit: int):
        """Traditional keyword search"""
        async with get_async_db() as db:
            # Search in content and symbols
            chunks = db.query(CodeEmbedding).join(CodeDocument).filter(
                CodeDocument.project_id == project_id,
                or_(
                    CodeEmbedding.chunk_content.ilike(f'%{query}%'),
                    CodeEmbedding.symbol_name.ilike(f'%{query}%')
                )
            ).limit(limit).all()

            results = []
            for chunk in chunks:
                results.append({
                    'chunk_id': chunk.id,
                    'content': chunk.chunk_content,
                    'document': {
                        'file_path': chunk.document.file_path,
                        'language': chunk.document.language,
                        'repo_name': chunk.document.repo_name
                    },
                    'search_type': 'keyword',
                    'score': self._calculate_keyword_score(query, chunk)
                })

            return results

    def _merge_results(self, semantic: List[Dict], keyword: List[Dict]) -> List[Dict]:
        """Merge and rank results from both search types"""
        # Combine with weighted scores
        all_results = {}

        # Add semantic results (weight: 0.7)
        for result in semantic:
            key = result['chunk_id']
            all_results[key] = result
            all_results[key]['final_score'] = result['score'] * 0.7

        # Add keyword results (weight: 0.3)
        for result in keyword:
            key = result['chunk_id']
            if key in all_results:
                all_results[key]['final_score'] += result['score'] * 0.3
            else:
                all_results[key] = result
                all_results[key]['final_score'] = result['score'] * 0.3

        # Sort by final score
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )

        return sorted_results
```

`backend/app/routers/search.py` (≤250 lines)
```python
@router.post("/search")
async def search_code(
    query: str,
    project_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unified search across code and documents"""
    # Default to user's projects if not specified
    if not project_ids:
        projects = db.query(Project).all()
        project_ids = [p.id for p in projects]

    # Initialize search
    vector_store = SQLiteVectorStore()
    embedding_generator = EmbeddingGenerator()
    hybrid_search = HybridSearch(vector_store, embedding_generator)

    # Perform search
    results = await hybrid_search.search(query, project_ids[0], filters, limit)

    # Format results
    formatted_results = []
    for result in results:
        formatted_results.append({
            'id': result['chunk_id'],
            'content': result['content'],
            'file_path': result['document']['file_path'],
            'language': result['document']['language'],
            'start_line': result.get('metadata', {}).get('start_line'),
            'end_line': result.get('metadata', {}).get('end_line'),
            'symbol': result.get('metadata', {}).get('symbol_name'),
            'score': result['final_score'],
            'search_type': result['search_type']
        })

    return {
        'query': query,
        'results': formatted_results,
        'total': len(formatted_results)
    }
```

### Day 13-14: Frontend Search Interface

**Tasks:**
1. Create search UI components
2. Add search result preview
3. Implement syntax highlighting
4. Build filtering interface

**Deliverables:**

`frontend/src/pages/SearchPage.jsx` (≤300 lines)
```jsx
import { useState, useCallback } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import SearchBar from '../components/search/SearchBar';
import SearchResults from '../components/search/SearchResults';
import SearchFilters from '../components/search/SearchFilters';
import { searchAPI } from '../api/search';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    language: null,
    fileType: null,
    project: null
  });

  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery.length >= 3) {
      performSearch();
    } else {
      setResults([]);
    }
  }, [debouncedQuery, filters]);

  const performSearch = async () => {
    setLoading(true);
    try {
      const response = await searchAPI.search({
        query: debouncedQuery,
        filters,
        limit: 50
      });
      setResults(response.results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="border-b bg-white p-4">
        <SearchBar
          value={query}
          onChange={setQuery}
          placeholder="Search code, functions, or use @project tags..."
          loading={loading}
        />
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-64 border-r bg-gray-50 p-4">
          <SearchFilters
            filters={filters}
            onChange={setFilters}
            availableLanguages={['python', 'javascript', 'typescript']}
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          <SearchResults
            results={results}
            query={debouncedQuery}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
}
```

`frontend/src/components/search/CodeSnippet.jsx` (≤200 lines)
```jsx
import { memo } from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python';
import javascript from 'react-syntax-highlighter/dist/esm/languages/hljs/javascript';
import typescript from 'react-syntax-highlighter/dist/esm/languages/hljs/typescript';

// Register languages
SyntaxHighlighter.registerLanguage('python', python);
SyntaxHighlighter.registerLanguage('javascript', javascript);
SyntaxHighlighter.registerLanguage('typescript', typescript);

const CodeSnippet = memo(({ content, language, startLine, highlightLines = [] }) => {
  return (
    <div className="relative">
      <div className="absolute top-2 right-2">
        <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">
          {language}
        </span>
      </div>

      <SyntaxHighlighter
        language={language}
        style={atomOneDark}
        showLineNumbers
        startingLineNumber={startLine || 1}
        wrapLines
        lineProps={lineNumber => {
          const isHighlighted = highlightLines.includes(lineNumber);
          return {
            style: {
              backgroundColor: isHighlighted ? '#364152' : 'transparent',
              display: 'block',
              width: '100%'
            }
          };
        }}
      >
        {content}
      </SyntaxHighlighter>
    </div>
  );
});

export default CodeSnippet;
```

### Day 15: Dependency Graph Visualization

**Tasks:**
1. Create dependency extraction
2. Build graph data structure
3. Implement D3.js visualization
4. Add interactive features

**Deliverables:**

`backend/app/code_processing/dependency_graph.py` (≤200 lines)
```python
from typing import Dict, List, Set
import json

class DependencyAnalyzer:
    """Extract and analyze code dependencies"""

    def build_dependency_graph(self, project_id: int) -> Dict:
        """Build dependency graph for a project"""
        with get_db() as db:
            documents = db.query(CodeDocument).filter_by(
                project_id=project_id
            ).all()

            nodes = []
            edges = []
            node_map = {}

            # Create nodes for each file
            for doc in documents:
                node_id = f"file_{doc.id}"
                nodes.append({
                    'id': node_id,
                    'label': doc.file_path.split('/')[-1],
                    'file_path': doc.file_path,
                    'type': 'file',
                    'language': doc.language
                })
                node_map[doc.file_path] = node_id

            # Create edges based on imports
            for doc in documents:
                if doc.imports:
                    source_id = f"file_{doc.id}"
                    for imp in doc.imports:
                        # Resolve import to file path
                        target_path = self._resolve_import(imp, doc.file_path)
                        if target_path in node_map:
                            edges.append({
                                'source': source_id,
                                'target': node_map[target_path],
                                'type': 'import'
                            })

            return {
                'nodes': nodes,
                'edges': edges,
                'stats': {
                    'total_files': len(nodes),
                    'total_dependencies': len(edges)
                }
            }
```

`frontend/src/components/knowledge/DependencyGraph.jsx` (≤300 lines)
```jsx
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function DependencyGraph({ projectId }) {
  const svgRef = useRef(null);
  const [graphData, setGraphData] = useState(null);

  useEffect(() => {
    fetchGraphData();
  }, [projectId]);

  useEffect(() => {
    if (graphData) {
      renderGraph();
    }
  }, [graphData]);

  const fetchGraphData = async () => {
    const data = await api.get(`/api/projects/${projectId}/dependency-graph`);
    setGraphData(data);
  };

  const renderGraph = () => {
    const width = 800;
    const height = 600;

    // Clear previous graph
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    // Create force simulation
    const simulation = d3.forceSimulation(graphData.nodes)
      .force("link", d3.forceLink(graphData.edges).id(d => d.id))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    // Add links
    const link = svg.append("g")
      .selectAll("line")
      .data(graphData.edges)
      .enter().append("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6);

    // Add nodes
    const node = svg.append("g")
      .selectAll("circle")
      .data(graphData.nodes)
      .enter().append("circle")
      .attr("r", 10)
      .attr("fill", d => getNodeColor(d.language))
      .call(drag(simulation));

    // Add labels
    const label = svg.append("g")
      .selectAll("text")
      .data(graphData.nodes)
      .enter().append("text")
      .text(d => d.label)
      .attr("font-size", 12)
      .attr("dx", 15)
      .attr("dy", 4);

    // Update positions on tick
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

      label
        .attr("x", d => d.x)
        .attr("y", d => d.y);
    });
  };

  return (
    <div className="dependency-graph">
      <svg ref={svgRef}></svg>
    </div>
  );
}
```

---

## Database Migrations

`backend/alembic/versions/003_add_code_tables.py`
```python
def upgrade():
    # Create code_documents table
    op.create_table(
        'code_documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('repo_name', sa.String(200)),
        sa.Column('commit_sha', sa.String(40)),
        sa.Column('language', sa.String(50)),
        sa.Column('file_size', sa.Integer()),
        sa.Column('last_modified', sa.DateTime()),
        sa.Column('symbols', sa.JSON()),
        sa.Column('imports', sa.JSON()),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('is_indexed', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.Index('idx_code_document_project', 'project_id'),
        sa.Index('idx_code_document_path', 'file_path'),
        sa.Index('idx_code_document_hash', 'content_hash')
    )

    # Create code_embeddings table
    op.create_table(
        'code_embeddings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('code_documents.id'), nullable=False),
        sa.Column('chunk_content', sa.Text(), nullable=False),
        sa.Column('symbol_name', sa.String(200)),
        sa.Column('symbol_type', sa.String(50)),
        sa.Column('start_line', sa.Integer()),
        sa.Column('end_line', sa.Integer()),
        sa.Column('embedding', sa.JSON()),
        sa.Column('embedding_model', sa.String(50), default='text-embedding-3-small'),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Index('idx_embedding_document', 'document_id'),
        sa.Index('idx_embedding_symbol', 'symbol_name')
    )
```

---

## Dependencies to Add

`backend/requirements.txt` additions:
```
tree-sitter==0.20.4
GitPython==3.1.40
openai==1.12.0
tiktoken==0.5.2
numpy==1.26.3
tenacity==8.2.3
aiofiles==23.2.1
```

`frontend/package.json` additions:
```json
"d3": "^7.8.5",
"react-syntax-highlighter": "^15.5.0",
"lodash.debounce": "^4.0.8"
```

---

## Configuration Updates

`.env.example` additions:
```env
# OpenAI API
OPENAI_API_KEY=your-key-here
OPENAI_ORG_ID=optional-org-id
EMBEDDING_MODEL=text-embedding-3-small

# Code Processing
MAX_FILE_SIZE_MB=10
SUPPORTED_LANGUAGES=python,javascript,typescript
CHUNK_SIZE_TOKENS=500

# Vector Store
VECTOR_DB_PATH=data/vectors.db
```

---

## Success Criteria

1. ✅ Files can be uploaded and parsed with tree-sitter
2. ✅ Git repositories can be cloned and processed
3. ✅ Code is intelligently chunked by symbols
4. ✅ Embeddings are generated for all chunks
5. ✅ Semantic search returns relevant results
6. ✅ Dependency graph visualizes relationships
7. ✅ Search UI is intuitive and fast
8. ✅ No modules exceed 900 lines

---

## Performance Optimizations

1. **Batch Processing**: Process files in batches of 10
2. **Async Operations**: Use async/await throughout
3. **Caching**: Cache parsed ASTs for frequently accessed files
4. **Incremental Updates**: Only process changed files in git repos
5. **Lazy Loading**: Generate embeddings on-demand for large projects

---

## Next Phase Preview

Phase 5 will implement the chat system:
- WebSocket-based real-time chat
- Code-aware context building
- Slash command implementation
- LLM integration with streaming
- Split-pane chat/code interface

This phase provides the foundation for intelligent code understanding while keeping the implementation practical and maintainable for a small team.
