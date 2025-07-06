# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# AI Productivity App - Developer Guide

Modern AI productivity application with React frontend and FastAPI backend, supporting chat, project management, code analysis, and knowledge management features.

## Quick Start

```bash
make install    # one-time setup (backend & frontend deps)
make dev        # start full stack via docker-compose
# → Frontend: http://localhost:5173
# → Backend API: http://localhost:8000
# → API Docs: http://localhost:8000/docs
```

## Architecture Overview

**Backend (FastAPI + SQLAlchemy)**
- `backend/app/main.py` - Application entry point with middleware stack (CORS, security, correlation IDs)
- `backend/app/config.py` - Pydantic settings with environment-driven configuration
- `backend/app/routers/` - REST endpoints organized by domain (auth, projects, chat, code, search, etc.)
- `backend/app/models/` - SQLAlchemy models (User, Project, ChatSession, CodeDocument, etc.) 
- `backend/app/services/` - Business logic (chat, search, embedding, vector stores)
- `backend/app/middleware/` - Custom middleware (security headers, rate limiting, request correlation)
- `backend/app/websocket/` - WebSocket handlers for real-time chat functionality

**Frontend (React 19 + Vite)**
- `frontend/src/pages/` - Route components (Dashboard, ProjectChatPage, SearchPage, etc.)
- `frontend/src/components/` - Reusable UI components organized by domain
- `frontend/src/hooks/` - Custom React hooks (useChat, useWebSocket, useProjects, etc.)
- `frontend/src/api/` - API client modules matching backend routers
- `frontend/src/stores/` - Zustand state management (auth, chat, projects)
- `frontend/src/contexts/` - React contexts (AuthContext, ModelContext, KnowledgeContext)

## Core Development Commands

**Container Management**
- `make dev` - Start full development stack (builds images, runs containers)
- `make up` / `make down` - Start/stop containers in background
- `make logs` - View container logs
- `make status` - Check service health status
- `make build` - Build Docker images only

**Testing & Quality**
- `make test` - Run all tests (backend pytest + frontend vitest)
- `make lint` - Run all linters (flake8, mypy, eslint)
- `make format` - Format code (black, prettier)
- `make check` - Run lint + test (pre-commit checks)

**Individual Commands**
- Backend: `cd backend && python -m pytest -v --cov=app`
- Frontend: `cd frontend && npm test` or `npm run test:coverage`
- Single backend test: `cd backend && python -m pytest tests/test_specific.py::test_name -v`
- Frontend test watch: `cd frontend && npm test`

**Database Operations**
- `make db-reset` - Drop and recreate database
- `make db-shell` - Open SQLite shell
- `cd backend && alembic upgrade head` - Apply migrations
- `cd backend && alembic revision --autogenerate -m "description"` - Create migration

## Key Environment Variables

Place these in `.env` at repository root:

**Core Application**
- `SECRET_KEY` / `JWT_SECRET_KEY` - Must be set (not default value) for security
- `DATABASE_URL` - Defaults to PostgreSQL, falls back to SQLite in development
- `INSECURE_COOKIES=true` - Required for localhost development (no HTTPS)

**LLM Configuration**
- `LLM_PROVIDER=openai` (default) or `azure`
- `OPENAI_API_KEY` - Required for OpenAI provider
- `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` - Required when using Azure
- `LLM_MODEL=gpt-3.5-turbo` - Default model, overrideable per request

**Vector Store (Optional)**
- `VECTOR_STORE_TYPE=sqlite_vss` (default) or `qdrant`
- `QDRANT_URL=http://localhost:6333` - When using Qdrant backend

## WebSocket Architecture

The application uses WebSockets for real-time chat functionality:

**Backend WebSocket Implementation**
- `backend/app/websocket/manager.py` - WebSocket connection manager with per-session tracking
- `backend/app/websocket/handlers.py` - Message routing and processing
- `backend/app/routers/chat.py` - WebSocket endpoint at `/ws/sessions/{session_id}`
- Authentication via cookie (`access_token`) or query parameter (`?token=`)

**Frontend WebSocket Hooks**
- `frontend/src/hooks/useWebSocket.js` - Low-level WebSocket connection management
- `frontend/src/hooks/useWebSocketChannel.js` - Channel-based WebSocket abstraction
- `frontend/src/hooks/useChat.js` - Chat-specific WebSocket integration with message handling

## Core Architectural Patterns

**Backend Service Layer**
- Services in `backend/app/services/` handle complex business logic
- `chat_service.py` - Chat session management and message processing
- `vector_service.py` - Embedding generation and similarity search
- `hybrid_search.py` - Combined keyword + semantic search
- `embedding_service.py` - Vector embedding operations

**Frontend State Management**
- Zustand stores for global state (`authStore`, `chatStore`, `projectStore`)
- React Query for server state management and caching
- Context providers for feature-specific state (auth, models, knowledge)

**Security & Middleware Stack**
- CORS middleware with configurable origins
- Rate limiting via `slowapi` with Redis backend
- Security headers and CSRF protection
- Request correlation IDs for tracing

## Key Integrations

**Vector Search**
- Supports both SQLite-VSS (default) and Qdrant backends
- Embedding generation via OpenAI or Azure OpenAI
- Hybrid search combining keyword and semantic matching

**Code Analysis**
- Tree-sitter parsing for multiple programming languages
- Repository ingestion with Git integration
- Chunk-based document processing for large codebases

**Authentication**
- JWT tokens stored in HTTP-only cookies
- Session-based authentication with SQLAlchemy models
- Support for registration, login, password reset flows

## Development Workflow

When adding new features:

1. **Backend changes**: Add models → create migration → implement service → add router → write tests
2. **Frontend changes**: Create API client → implement hooks → build components → add to router → write tests  
3. **Always run**: `make lint` and `make test` before committing
4. **Database changes**: Use Alembic migrations, never modify schema directly

## Production Considerations

- Set `INSECURE_COOKIES=false` for HTTPS deployments
- Use PostgreSQL instead of SQLite for production
- Configure proper CORS origins for your domain
- Set strong `JWT_SECRET_KEY` (required, will fail startup if using default)
- Consider Qdrant for production vector search at scale

## Docker Services Architecture

The application runs as a multi-service Docker stack:

- **backend** - FastAPI application (port 8000)
- **frontend** - React/Vite application (port 5173) 
- **redis** - Session storage and rate limiting (port 6380)
- **qdrant** - Vector database for embeddings (port 6333)
- **render-svc** - Rendering service for complex outputs (port 8001)

**Quick Start Alternative**
```bash
./start.sh  # Alternative to make dev, handles Docker automatically
```

## Key Development Files

- `start.sh` - Quick start script for new developers
- `docker-compose.yml` - Multi-service container orchestration
- `backend/alembic/` - Database migrations (use `alembic revision --autogenerate`)
- `.env` - Environment variables (required for development)

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
