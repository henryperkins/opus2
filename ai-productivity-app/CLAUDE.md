# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI productivity application built for small teams (2-3 users) with a React frontend and FastAPI backend. The project uses a clean, modular architecture with modules kept under 900 lines.

**Phase 2 Status: ✅ COMPLETE**
- Full user authentication system implemented
- JWT-based session management
- Secure password hashing with bcrypt
- Rate limiting and CSRF protection
- Protected routes and user management
- Comprehensive frontend auth integration

**Phase 3 Status: ✅ COMPLETE**
- Full project management system implemented
- Project CRUD operations with status tracking (Active/Archived/Completed)
- Visual customization (color coding and emoji identification)
- Flexible tag system for project categorization
- Timeline event system tracking all project changes
- Search and filtering by status, tags, title, and description
- Responsive UI with optimistic updates and error handling
- Comprehensive project dashboard with pagination

**Phase 4 Status: ✅ COMPLETE — Code Intelligence Layer**
- Code file upload with language auto-detection
- Git repository integration (clone/pull & incremental diff processing)
- Tree-sitter powered parsing for Python / JavaScript / TypeScript
- Semantic chunking by symbol with token aware splitting
- OpenAI embeddings generation (text-embedding-3-small) with async batch processing
- SQLite VSS vector store with hybrid (semantic + keyword) search
- Dependency graph extraction & interactive D3.js visualization
- Vector, search, and parsing modules kept under the 900-line guideline

**Phase 5 Status: 🚧 IN PROGRESS — Real-time Chat & AI Assistance**
- WebSocket infrastructure with connection manager
- Persistent ChatSession & ChatMessage models (edit / soft-delete supported)
- Slash command framework (`/explain`, `/generate-tests`, …)
- Streaming LLM integration (OpenAI chat completions via server-sent events)
- Secret scanner & redaction for outbound messages
- Split-pane chat / code UI with syntax highlighted snippets
- Remaining work: advanced citation view & conversation summarisation

## Development Commands

### Quick Start (Simplified)
```bash
# One-command startup (handles everything)
./start.sh            # First run: installs deps + starts app
                      # Subsequent runs: just starts app

# Alternative commands
make dev              # Start development environment with Docker
make down             # Stop all containers
make status           # Check health of all services
```

### Backend Development
```bash
# Dependencies and setup
cd backend && pip install -r requirements.txt

# Local development (without Docker)
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing and quality
cd backend && python -m pytest -v --cov=app --cov-report=term-missing
cd backend && flake8 app --max-line-length=100
cd backend && mypy app --ignore-missing-imports
cd backend && black app tests
```

### Frontend Development
```bash
# Dependencies and setup
cd frontend && npm install

# Local development (without Docker)
cd frontend && npm run dev        # Vite dev server on port 5173
cd frontend && npm run build      # Production build
cd frontend && npm run preview    # Preview production build

# Testing and quality
cd frontend && npm test           # Currently placeholder
cd frontend && npm run lint       # ESLint
cd frontend && npx prettier --write "src/**/*.{js,jsx,css}"
```

### Database Management
```bash
make db-reset         # Reset SQLite database
make db-shell         # Open SQLite shell
# Vector store lives in data/vectors.db (auto created on first run)
```

### Quality Assurance
```bash
make lint             # Run all linters (backend + frontend)
make format           # Format all code (backend + frontend)
make test             # Run all tests
make check            # Run pre-commit checks (lint + test)
```

## Architecture

### Backend Structure (FastAPI + SQLAlchemy)
- `app/main.py` - FastAPI application entry point with middleware and lifespan management
- `app/routers/` - API route handlers (auth, monitoring, projects)
- `app/models/` - SQLAlchemy ORM models (User, Project, TimelineEvent)
- `app/schemas/` - Pydantic schemas for request/response validation
- `app/services/` - Business logic layer (project operations, timeline tracking)
- `app/database.py` - Database configuration and initialization
- `app/config.py` - Application settings and configuration
- `app/auth/` - Authentication and security utilities
- `app/middleware/` - Custom middleware (security, rate limiting)

### Code Intelligence Layer (Phase-4)
- `app/code_processing/` – Parsing, chunking & git helpers
  - `parser.py` – Tree-sitter wrapper & symbol extraction
  - `chunker.py` – Token aware semantic chunking
  - `git_integration.py` – Repository clone/update & diffing
- `app/embeddings/` – OpenAI embedding generator & batch processor
  - `generator.py`, `batch_processor.py`, `cache.py`
- `app/search/` – Hybrid semantic/keyword search
  - `vector_store.py` – SQLite VSS wrapper
  - `hybrid.py`, `filters.py`, `ranker.py`
- `app/models/code.py` – `CodeDocument` & `CodeEmbedding` ORM models

### Chat System (Phase-5)
- `app/websocket/` – Realtime WebSocket manager & handlers
- `app/chat/` – Context builder, slash-command implementations, secret scanner
- `app/services/chat_service.py` – Business logic for chat sessions / messages
- `app/llm/` – Provider abstraction + streaming client for OpenAI / Azure
- `app/routers/chat.py` – HTTP + WS endpoints for chat operations

### Frontend Structure (React + Vite)
- `src/main.jsx` - React application entry point
- `src/router.jsx` - React Router configuration
- `src/contexts/AuthContext.jsx` - Authentication context provider
- `src/components/` - Reusable React components organized by feature
  - `auth/` - Authentication components (Login, Register, UserMenu)
  - `projects/` - Project management components (ProjectCard, Timeline, Filters)
  - `common/` - Shared components (Header, Modal, ErrorBoundary)
- `src/pages/` - Top-level page components (Dashboard, ProjectsPage, LoginPage)
- `src/api/` - API client modules for backend communication
- `src/stores/` - Zustand state management stores (auth, projects)
- `src/hooks/` - Custom React hooks (useAuth, useProjects, useProjectSearch)

### New Frontend Modules
- `src/components/search/` – Search bar, result list & code snippet components
- `src/components/knowledge/` – Dependency graph visualisation (D3)
- `src/components/chat/` – Realtime chat UI & slash-command palette
- `src/pages/SearchPage.jsx` – Unified code/document search experience
- `src/pages/ChatPage.jsx` – Split-pane chat / code interface (WS powered)

### Key Patterns
- **Modular Architecture**: Features are organized into self-contained modules
- **Separation of Concerns**: Clear boundaries between data access, business logic, and presentation
- **Type Safety**: Pydantic for backend validation, PropTypes/JSDoc for frontend
- **Error Handling**: Consistent error responses and proper HTTP status codes
- **Health Checks**: Backend provides `/health` endpoints for monitoring

### Development Environment
- **Docker Compose**: Complete development environment with hot reloading
- **SQLite Database**: Local development database in `data/app.db`
- **CORS Configuration**: Frontend (port 5173) communicates with backend (port 8000)
- **Environment Variables**: Configure via `.env` files or Docker environment

### Testing Strategy
- **Backend**: pytest with coverage reporting and async support
  - Project CRUD operation tests in `tests/test_projects.py`
  - Timeline event functionality testing
  - Authentication and authorization tests
  - Code parsing & chunking tests in `tests/test_code_processing.py`
  - Hybrid search ranking tests in `tests/test_search.py`
  - Chat session lifecycle tests in `tests/test_chat.py`
- **Frontend**: Test framework TBD (placeholder currently)
- **Integration**: Health check endpoints for service verification

### Database Schema
- **Users**: Authentication and user management
- **Projects**: Core project data with status, visual customization, and tags
- **Timeline Events**: Activity tracking for all project changes
- **Proper Relations**: Foreign keys and cascading deletes for data integrity

- **CodeDocuments**: Parsed code files & metadata (symbols, imports, hash)
- **CodeEmbeddings**: Semantic chunks with vector embeddings
- **ChatSessions & ChatMessages**: Real-time chat persistence

## Port Configuration
- Frontend: http://localhost:5173 (Vite dev server)
- Backend: http://localhost:8000 (FastAPI with auto-reload)
- API Documentation: http://localhost:8000/docs (development only)