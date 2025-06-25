# Guard Rails: AI Productivity App

This document outlines mandatory guard rails (constraints, standards, and best practices) for contributing to, deploying, and operating the AI Productivity App. Adhering to these guidelines is essential for maintaining security, stability, code quality, and user trust.

---

## Single Sources of Truth (SSOT)

The following are implementation-verified single sources of truth. All contributors MUST reference and update these concrete sources, as established in code, to avoid duplication, drift, or ambiguity in business logic, configuration, data, and application state.

### Backend SSOTs

- **Application Configuration**
  - [`Settings`](backend/app/config.py#L12) class in [`backend/app/config.py`](backend/app/config.py):
    - Loads all runtime configuration for the backend from environment variables using Pydantic BaseSettings.
    - All environment-driven logic must derive from this class.
    - Any new config must be added as a field to `Settings` and documented in `.env.example`.
    - Handles absolute database path resolution to avoid CWD-dependent issues.

- **Database Models (Authoritative Data Schema)**
  - SQLAlchemy model classes in [`backend/app/models/`](backend/app/models/):
    - **Core Models**: [`User`](backend/app/models/user.py), [`Project`](backend/app/models/project.py), [`Session`](backend/app/models/session.py)
    - **Chat System**: [`ChatSession`](backend/app/models/chat.py), [`ChatMessage`](backend/app/models/chat.py)
    - **Project Features**: [`TimelineEvent`](backend/app/models/timeline.py)
    - **Code Analysis**: [`CodeDocument`](backend/app/models/code.py), [`CodeEmbedding`](backend/app/models/code.py)
    - **Search**: [`SearchHistory`](backend/app/models/search_history.py)
    - **Background Jobs**: [`ImportJob`](backend/app/models/import_job.py)
    - These classes define the full canonical persisted data shape for all project entities.
    - Any database change must update both the ORM class and generate a corresponding migration in [`backend/alembic/versions/`](backend/alembic/versions/).

- **Core Business Logic and Validation**
  - Service layer modules in [`backend/app/services/`](backend/app/services/):
    - [`ProjectService`](backend/app/services/project_service.py): Project CRUD, timeline management, statistics
    - [`ChatService`](backend/app/services/chat_service.py): Chat session/message management, WebSocket broadcasting
  - Model-level validation with `@validates` decorators in all model classes
  - All business/process rules must reside here, not as duplicated frontend or adhoc logic.

### Frontend SSOTs

- **Global Data Fetching & Caching**
  - **TanStack Query `QueryClient` singleton** in [`frontend/src/queryClient.js`](frontend/src/queryClient.js):
    - Central source of truth for *all* remote data the browser knows about.
    - Provides caching, optimistic updates, de-duplication and refetch orchestration.
    - Components and hooks **must** obtain server data through
      `useQuery / useMutation` bound to this client – never via ad-hoc `axios` calls.

- **Hybrid State Management Architecture**
  - **Server State**: TanStack Query for all remote data and API interactions
  - **Client State**: Zustand stores for local application state:
    - [`useProjectStore`](frontend/src/stores/projectStore.js): Project data, filters, pagination, and state updates
    - [`useAuthStore`](frontend/src/stores/authStore.js): User preferences (theme, settings) and session metadata
    - [`useChatStore`](frontend/src/stores/chatStore.js): Chat-specific client state and UI preferences
  - **Runtime Context**: React Context for cross-cutting concerns:
    - [`AuthContext`](frontend/src/contexts/AuthContext.jsx): Authentication runtime state powered by TanStack Query (`useQuery(['me'])`)

- **Primary Chat Interface**
  - [`ProjectChatPage`](frontend/src/pages/ProjectChatPage.jsx): **Main chat interface** replacing removed ChatPage.jsx
    - Integrated code execution, knowledge base, and AI model selection
    - Mobile-first responsive design with bottom sheet integration
    - Enhanced message rendering with streaming support and citations
    - WebSocket-powered real-time communication

- **Project Interaction Hooks**
  - Custom hooks in [`frontend/src/hooks/useProjects.js`](frontend/src/hooks/useProjects.js):
    - `useProject()`: Single project management
    - `useProjectSearch()`: Search and filtering
    - `useProjectTimeline()`: Timeline event management
  - Chat interaction hooks in [`frontend/src/hooks/useChat.js`](frontend/src/hooks/useChat.js) – built on
    [`useWebSocketChannel`](frontend/src/hooks/useWebSocketChannel.js) for resilient real-time updates.
  - Knowledge and search hooks:
    - [`useCodeSearch`](frontend/src/hooks/useCodeSearch.js): Code-specific search functionality
    - [`useKnowledgeContext`](frontend/src/hooks/useKnowledgeContext.js): Knowledge base integration
  - Auth hooks in [`frontend/src/hooks/useAuth.js`](frontend/src/hooks/useAuth.js): `useAuth()`, `useUser()`, `useRequireAuth()`
  - AI/Model hooks:
    - [`useModelSelect`](frontend/src/hooks/useModelSelect.js): AI model selection and configuration
    - [`useCodeExecutor`](frontend/src/hooks/useCodeExecutor.js): Code execution pipeline integration

- **Mobile-First Design System**
  - [`MobileBottomSheet`](frontend/src/components/common/MobileBottomSheet.jsx): Advanced mobile UI with gesture support
  - [`useMediaQuery`](frontend/src/hooks/useMediaQuery.js): Responsive design helper for breakpoint management
  - Mobile-optimized layouts in primary interfaces (ProjectChatPage, knowledge panels)

_Legacy SWR has been fully removed as of 2025-W22._

### Global/Platform SSOTs

- **Environment and Secret Management**
  - Configuration values and secrets live in:
    - [`.env`](.env), [`.env.example`](.env.example), [`backend/.env`](backend/.env), [`frontend/.env`](frontend/.env)
    - **Never** copy or partially duplicate these values in code or in documentation.
    - The `Settings` class in `backend/app/config.py` is the sole interface for accessing environment variables.

- **Database Schema and Migrations**
  - Alembic migrations in [`backend/alembic/versions/`](backend/alembic/versions/)
  - Migration history and environment in [`backend/alembic/env.py`](backend/alembic/env.py)
  - Database URL resolution handled centrally in `Settings._DEFAULT_DB_PATH`

### Documentation SSOT

- **Team/Public Process/Architecture**
  - Markdown documents in [`docs/`](docs/), including [`GUARDRAILS.md`](GUARDRAILS.md).
  - Process and operational changes must be reflected here and tied to their technical SSOT references.

---

**Risks of Violating These SSOTs:**
- Configuration drift and database inconsistencies
- Silent application errors and broken API contracts
- Security vulnerabilities from bypassed validation layers
- Inconsistent UX/business logic across frontend/backend
- WebSocket connection management failures
- Chat state synchronization issues

**Mandate:**
All pull requests or changes impacting these artifacts *must* explicitly reference the affected SSOT(s) in their description or changelogs. Any implementation ambiguity must be triaged by examining these concrete sources in code.

---

## 1. Code Quality & Standards

- **Style Guides:**
  - **Python:** Follow [PEP8](https://www.python.org/dev/peps/pep-0008/) and enforce with `pylint`/`black`/`ruff`.
  - **JavaScript/React:** Follow [Airbnb JS](https://github.com/airbnb/javascript) or ESLint-configured repo guidelines.
- **Type Safety:**
  - Use type hints for Python (mypy when possible).
  - Apply TypeScript or JSDoc in React as appropriate.
- **Code Reviews:**
  - All code changes MUST be peer-reviewed via Pull Requests.
  - Automated linting and formatting checks must pass before merge.
- **Documentation:**
  - All public-facing functions, classes, and API endpoints must have docstrings or JSDoc.
  - Update and maintain docs in `/docs` for feature changes.

---

## 2. Security Practices

- **Secret Management:**
  - **Never commit secrets:** API keys, credentials, and private keys MUST NOT be committed to source control. Use environment variables or secret stores.
  - Use `.env.example` to document required env vars.
  - All secrets accessed through the `Settings` class configuration layer.

- **Authentication & Authorization:**
  - JWT tokens with HttpOnly cookies for session management
  - Session tracking via [`Session`](backend/app/models/session.py) model with JTI (JWT ID) validation
  - Rate limiting: 5 attempts per minute per IP address on auth endpoints
  - Password hashing using bcrypt with cost factor 12
  - Support for invite-code based registration when enabled

- **CSRF Protection:**
  - Double-submit cookie pattern with `csrftoken` cookie and `X-CSRFToken` header
  - CSRF validation enforced on all state-changing requests (POST, PUT, PATCH, DELETE)
  - Auth endpoints exempted from CSRF (rely on rate limiting instead)

- **Security Headers:**
  - CSP (Content Security Policy) with strict directives
  - HSTS (HTTP Strict Transport Security) with preload
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - Referrer-Policy: same-origin

- **WebSocket Security:**
  - JWT token validation required for all WebSocket connections
  - User authentication checked before processing any WebSocket messages
  - Connection lifecycle managed with proper cleanup

- **Dependency Management:**
  - Use `pip-audit`, `npm audit`, or equivalent to scan for vulnerabilities before merging or releasing.
  - No direct installs from untrusted sources.
  - Optional dependencies (like passlib, python-jose) with graceful fallbacks for testing environments.

- **Input Validation & Sanitization:**
  - All user-generated data must be strictly validated and sanitized on backend and frontend.
  - Pydantic schemas for request/response validation
  - SQLAlchemy model validators with `@validates` decorators
  - Chat message content validation and sanitization

- **Vulnerability Disclosure:**
  - Promptly triage and remediate discovered vulnerabilities per the [ISSUE_REMEDIATION_PLAN.md](docs/ISSUE_REMEDIATION_PLAN.md).

---

## Critical Application Logic That Must Be Respected

The following application logic patterns and modules are essential for the correct, secure operation of the system. Any major feature, refactor, or integration must preserve or extend these mechanisms as implemented:

### Backend (Python/FastAPI)

- **API Endpoint Contracts:**
  - All route definitions in [`backend/app/routers/`](backend/app/routers/) (e.g., `auth.py`, `projects.py`, `chat.py`) contain parameter validation, role enforcement, and error handling. Do not bypass these contract layers with direct DB/script access.

- **Authentication, Sessions, and Security:**
  - Token issuance and session management logic is centralized in [`auth.py`](backend/app/routers/auth.py).
  - **SecurityHeadersMiddleware** ([`security.py`](backend/app/middleware/security.py)): Enforces required security headers and CSRF validation on every request.
  - **CSRF Protection**: Implements the **double-submit cookie** pattern.
    - Cookie name: `csrftoken`
    - Header name: `x-csrftoken` (case-insensitive – the backend lower-cases header keys before comparison, so `X-CSRFToken` sent by the browser/axios also works).
    - The authoritative constant is `CSRF_HEADER_NAME = "x-csrftoken"` in [`backend/app/auth/security.py`](backend/app/auth/security.py).

    > Historical note: earlier versions of this document claimed the header had to be `X-CSRFToken` *only*. In practice the backend treats the header in a case-insensitive manner, and the constant in code is lower-case. The wording has been updated to remove this discrepancy.
  - **CORS** ([`cors.py`](backend/app/middleware/cors.py)): Only origins allowed by `Settings.cors_origins_list` are permitted access.
  - **Rate-limiting:** Custom in-memory rate limiting via `enforce_rate_limit()` in [`security.py`](backend/app/auth/security.py).

- **Permissions and Authentication Dependencies:**
  - Permission enforcement via [`dependencies.py`](backend/app/dependencies.py):
    - `CurrentUserRequired`: Enforces authentication with HTTP 401 if not authenticated
    - `CurrentUserOptional`: Provides user if authenticated, None otherwise
    - `DatabaseDep`: Provides SQLAlchemy session dependency
  - All protected endpoints must use these dependencies.

- **Business Logic — Service Layer:**
  - Service-layer enforcement and cross-entity business rules reside in [`backend/app/services/`](backend/app/services/):
    - **ProjectService**: Project lifecycle, timeline events, statistics calculations
    - **ChatService**: Message management, session handling, WebSocket broadcasting
  - Never bypass service layer for business operations.

- **WebSocket Safety:**
  - WebSocket endpoints in [`chat.py`](backend/app/routers/chat.py) must always perform auth via `get_current_user_ws()` before processing any data.
  - WebSocket connection management handled by [`connection_manager`](backend/app/websocket/manager.py).
  - Chat message broadcasting managed through `ChatService._broadcast_message()`.

- **Database Operations:**
  - All database writes must go through service layer or router endpoints.
  - ORM model validation via `@validates` decorators is enforced.
  - Database sessions managed via `DatabaseDep` dependency.

### Frontend (React/JS)

- **Authentication and Access Gating:**
  - `useRequireAuth()` in [`useAuth.js`](frontend/src/hooks/useAuth.js) must be used to protect any page/component that requires login.
  - Dual auth state management: `AuthContext` for runtime state, `useAuthStore` for persistence.
  - Never manually implement custom auth guards outside these patterns.

- **Data Loading and Canonical State:**
  - All project operations must route through canonical hooks and stores:
    - [`useProject()`](frontend/src/hooks/useProjects.js), [`useProjectSearch()`](frontend/src/hooks/useProjects.js), [`useProjectTimeline()`](frontend/src/hooks/useProjects.js)
    - [`useProjectStore`](frontend/src/stores/projectStore.js) for all project state management
    - [`useChat()`](frontend/src/hooks/useChat.js) for all chat-related actions and initialization
  - Chat interface must use [`ProjectChatPage`](frontend/src/pages/ProjectChatPage.jsx) as the single source of truth for chat UI
  - AI model selection must go through [`useModelSelect`](frontend/src/hooks/useModelSelect.js) hook
  - Code execution must use [`useCodeExecutor`](frontend/src/hooks/useCodeExecutor.js) for all code running operations
  - Never bypass these hooks for direct API calls in components.

- **HTTP Client Configuration:**
  - All API calls must use the configured [`client`](frontend/src/api/client.js) which handles:
    - CSRF token attachment via `X-CSRFToken` header
    - HttpOnly cookie management (`withCredentials: true`)
    - Automatic 401/403 handling with logout events
    - Exponential backoff retry for 5xx errors
  - Never create separate Axios instances without these configurations.

- **Mobile-First UI Patterns:**
  - [`MobileBottomSheet`](frontend/src/components/common/MobileBottomSheet.jsx) must be used for all mobile modal/overlay interfaces
  - Responsive breakpoints must be managed through [`useMediaQuery`](frontend/src/hooks/useMediaQuery.js) hook
  - Mobile knowledge panel state must be managed consistently across all chat interfaces
  - Touch gestures and swipe interactions must follow established patterns in MobileBottomSheet
  - Never implement custom mobile modals or overlays without using the established bottom sheet pattern

- **Enhanced Chat Architecture:**
  - Message rendering must use [`EnhancedMessageRenderer`](frontend/src/components/chat/EnhancedMessageRenderer.jsx) for consistent formatting
  - Command input must use [`EnhancedCommandInput`](frontend/src/components/chat/EnhancedCommandInput.jsx) for Monaco editor integration
  - Streaming messages must use [`StreamingMessage`](frontend/src/components/chat/StreamingMessage.jsx) component
  - Citations must be rendered via [`CitationRenderer`](frontend/src/components/chat/CitationRenderer.jsx)
  - Interactive elements must be processed through established callback patterns
  - Never implement custom message rendering outside these established components

- **Unified State Management Patterns:**
  - **Server State**: Must use TanStack Query (`useQuery`, `useMutation`) for all API data
  - **Client State**: Must use designated Zustand stores for local state:
    - Project data: `useProjectStore` only
    - User preferences: `useAuthStore` only  
    - Chat UI state: `useChatStore` only (when implemented)
  - **Cross-cutting State**: Use React Context sparingly, only for auth runtime state
  - **State Synchronization**: Server state changes must invalidate relevant TanStack Query cache keys
  - Never duplicate state across multiple stores or contexts
  - Never create ad-hoc state management outside established stores

- **TypeScript Migration Standards:**
  - All new components must be created as `.tsx` files with proper TypeScript
  - Existing `.jsx` files should be migrated to `.tsx` when touched for feature work
  - **Interface Definitions**: Create centralized interfaces in `frontend/src/types/`
  - **Prop Types**: All component props must have proper TypeScript interfaces
  - **API Response Types**: All API responses must have corresponding TypeScript types
  - **Hook Return Types**: Custom hooks must explicitly type their return values
  - **Event Handler Types**: Use proper React event handler types (`MouseEventHandler`, etc.)
  - Never use `any` type - use proper typing or `unknown` with type guards
  - Strict null checks must be enabled and respected

### Cross-Cutting Security Patterns

- **Never Bypass Middleware:**
  - Security, CSRF, and CORS middleware are always in force. All HTTP endpoints, even internal APIs, must pass through these chains.
  - Rate limiting applies to auth endpoints: 5 attempts per minute per IP.

- **No Direct DB or Store Modification:**
  - All writes must go through validated service, router, or store interfaces.
  - Never mutate the database or frontend global state directly from view/UI code or scripts.

- **WebSocket Authentication:**
  - All WebSocket connections must authenticate via JWT token validation.
  - Connection lifecycle managed through `connection_manager` with proper cleanup.

- **Environment Configuration:**
  - Database URL resolution uses absolute paths via `Settings._DEFAULT_DB_PATH` to avoid CWD issues.
  - CORS origins configured via `Settings.cors_origins_list`.
  - Cookie security settings controlled via `Settings.insecure_cookies`.

These layers collectively enforce application invariants, trust boundaries, and security requirements.

### Chat and WebSocket Management

- **WebSocket Connection Management:**
  - Connection lifecycle managed via [`ConnectionManager`](backend/app/websocket/manager.py):
    - Session-based connection grouping: `session_id -> List[WebSocket]`
    - User session tracking: `user_id -> Set[session_id]`
    - Thread-safe operations with asyncio locks
  - All WebSocket endpoints must authenticate users before accepting connections.

- **Chat System Architecture:**
  - [`ChatService`](backend/app/services/chat_service.py) handles all chat business logic:
    - Message CRUD operations with soft-delete support
    - Session management and timeline integration
    - Real-time broadcasting via WebSocket manager
  - [`ChatProcessor`](backend/app/chat/processor.py) handles AI interactions and command processing.
  - Chat slash commands implemented in [`backend/app/chat/commands.py`](backend/app/chat/commands.py):
    - `/explain`, `/generate-tests`, `/summarize-pr`, `/grep` commands
    - Extensible command registry pattern

- **Real-time Communication Patterns:**
  - All chat messages broadcast via `ChatService._broadcast_message()`
  - WebSocket message types: `new_message`, `message_updated`, `message_deleted`
  - Connection cleanup handled automatically on disconnect

### Code Analysis and LLM Integration

- **Code Processing Pipeline:**
  - [`CodeDocument`](backend/app/models/code.py) and [`CodeEmbedding`](backend/app/models/code.py) models for semantic search
  - [`ContextBuilder`](backend/app/chat/context_builder.py) extracts relevant code context for AI interactions
  - Integration with vector search capabilities for code understanding

- **LLM Client Architecture:**
  - Abstracted LLM client in [`backend/app/llm/client.py`](backend/app/llm/) with streaming support
  - Provider-agnostic implementation supporting OpenAI and Azure OpenAI
  - Streaming response handling via [`StreamingHandler`](backend/app/llm/streaming.py)

- **Search Capabilities:**
  - Hybrid search implementation combining text and semantic search
  - [`SearchHistory`](backend/app/models/search_history.py) tracking for user query patterns
  - Integration with chat commands for contextual code exploration

---

## 3. Data Privacy & Usage

- **Personal Data:**
  - Collect only necessary data; annotate any new PII fields and justify storage.
  - User data exports and deletions must be supported per applicable privacy regulations (GDPR, etc.).
- **Logging:**
  - Never log secrets or sensitive data. Audit logs for authentication and admin actions only.
- **Data Access:**
  - Use strict ORM queries to avoid unintentional data exposure or leaks.

---

## 4. Testing & Validation

- **Backend Testing:**
  - Comprehensive test suite in [`backend/tests/`](backend/tests/):
    - `test_auth.py`: Authentication, registration, JWT validation, rate limiting, CSRF
    - `test_projects.py`: Project CRUD, timeline events, authorization
    - `test_chat.py`: Chat sessions, message management, WebSocket functionality
  - Use pytest with SQLAlchemy test fixtures and FastAPI TestClient
  - Database transaction rollback for test isolation
  - Mock external dependencies (LLM clients, embedding services)

- **Frontend Testing:**
  - Jest and React Testing Library for component testing
  - Test coverage for auth flows, project management, and chat interactions
  - Mock API responses for isolated component testing
  - Integration tests for complete user workflows

- **Test Coverage:**
  - Minimum 80% code coverage goal, enforced in CI
  - Focus on business logic, security features, and critical user paths
  - Database model validation and schema migration testing

- **Security Testing:**
  - CSRF protection validation
  - Rate limiting behavior verification
  - JWT token expiration and validation testing
  - Input sanitization and validation testing
  - WebSocket authentication and authorization testing

- **Manual Validation:**
  - Major feature changes require manual QA checks for security and UX
  - Cross-browser compatibility testing for frontend features
  - Database migration testing on staging environments

---

## 5. Infrastructure & Deployment

- **Containerization:**
  - Docker and Docker Compose configuration in [`docker-compose.yml`](docker-compose.yml)
  - Backend service exposes port 8000 with health checks at `/health/ready`
  - Frontend service exposes port 5173 with hot-reload for development
  - Development containers use volume mounting for live code updates
  - Production containers should use multi-stage builds for minimal images

- **Environment Configuration:**
  - Development: `INSECURE_COOKIES=true` for HTTP cookie handling
  - Production: Remove `INSECURE_COOKIES` for Secure cookie attributes
  - Database path resolution handles different working directories automatically
  - CORS origins configured per environment via `CORS_ORIGINS` environment variable

- **Database Management:**
  - Alembic migrations for schema versioning in [`backend/alembic/versions/`](backend/alembic/versions/)
  - Automated table creation on startup via `init_db()` in [`backend/app/database.py`](backend/app/database.py)
  - Schema synchronization tools: `sync_database.py`, `verify_schema.py`

- **CI/CD Pipelines:**
  - All merges to `main` must pass full test, lint, and build pipelines.
  - Staging environment required; never deploy untested changes to production.
  - Backend tests include auth, chat, project management, and security features

- **Environment Parity:**
  - Staging and production environments should mirror each other closely (services, config, secrets).
  - Use identical Docker images with environment-specific configuration only.

---

## 6. API & Integration

- **External APIs:**
  - LLM integration supports OpenAI and Azure OpenAI providers
  - Provider configuration via environment variables (`LLM_PROVIDER`, `OPENAI_API_KEY`, `AZURE_OPENAI_*`)
  - All third-party integrations require threat model review
  - Validate all responses received from external APIs
  - Streaming response handling for real-time AI interactions

- **Internal API Design:**
  - RESTful endpoints in [`backend/app/routers/`](backend/app/routers/):
    - `/api/auth/*`: Authentication and user management
    - `/api/projects/*`: Project CRUD and timeline management
    - `/api/chat/*`: Chat sessions and message handling
  - WebSocket endpoints for real-time communication at `/api/chat/ws/sessions/{session_id}`
  - Pydantic request/response models in [`backend/app/schemas/`](backend/app/schemas/)

- **Rate Limits:**
  - Auth endpoints: 5 attempts per minute per IP address
  - Custom rate limiting implementation with in-memory storage for development
  - Configurable rate limit windows and thresholds

- **Error Handling:**
  - Never expose internal errors or stack traces publicly
  - Structured error responses with appropriate HTTP status codes
  - Centralized error handling in FastAPI exception handlers
  - Frontend error interceptors in [`frontend/src/api/client.js`](frontend/src/api/client.js)

- **Real-time Communication:**
  - WebSocket protocol for chat message broadcasting
  - Connection management with user session tracking
  - Graceful connection cleanup and error handling

---

## 7. Contribution Process

- **Pull Requests:**
  - PRs must link to an issue or describe their intent clearly.
- **Commit Messages:**
  - Use conventional commit messages (`feat:`, `fix:`, `docs:`, etc.).
- **Issue Templates:**
  - All issues (bugs/features) must use templates with clear reproduction steps or acceptance criteria.

---

## 8. Operational Guard Rails

- **Monitoring & Alerts:**
  - Set up monitoring (CPU, RAM, health, error rates) on all production components.
  - Alerting must be enabled for failure, downtime, or suspicious actions.
- **Backups & Disaster Recovery:**
  - Implement regular automated backups for all persistent data stores.
- **Incident Response:**
  - Define escalation steps and contacts for out-of-hours or critical incidents.

---

## 9. Prohibited Practices

- **Security Violations:**
  - Never bypass authentication or privilege checks for expedience
  - Never commit secrets, API keys, or credentials to source control
  - Do not disable CSRF protection or security middleware
  - Never expose internal error details or stack traces to clients

- **Architecture Violations:**
  - Do not bypass service layer for database operations
  - Never create direct database connections outside of `DatabaseDep`
  - Do not bypass Zustand stores for frontend state management
  - Never create separate HTTP clients without CSRF/auth configuration
  - Do not implement duplicate chat interfaces outside of `ProjectChatPage`
  - Never bypass established mobile UI patterns (`MobileBottomSheet`, `useMediaQuery`)
  - Do not create custom message rendering outside of established chat components

- **Development Practices:**
  - No feature toggling via untracked ad-hoc settings in production
  - Do not merge code with failing tests or security checks
  - Do not store business logic in database migrations or one-off scripts
  - Never mutate global state directly from UI components

- **WebSocket Violations:**
  - Do not accept WebSocket connections without user authentication
  - Never bypass `ConnectionManager` for WebSocket lifecycle management
  - Do not send messages without proper session validation

- **Configuration Violations:**
  - Never hardcode configuration values outside of `Settings` class
  - Do not override environment variables directly in code
  - Never use relative paths for database connections

- **Chat System Violations:**
  - Do not bypass `ChatService` for message operations
  - Never directly manipulate chat state without WebSocket notifications
  - Do not implement custom command handlers outside the registry pattern
  - Do not create chat interfaces outside of `ProjectChatPage` architecture
  - Never bypass `useModelSelect` for AI model selection
  - Do not implement custom interactive element handlers outside established patterns

- **Mobile UX Violations:**
  - Never implement custom mobile overlays without using `MobileBottomSheet`
  - Do not hardcode breakpoints - use `useMediaQuery` hook
  - Never create inconsistent mobile knowledge panel implementations
  - Do not bypass established responsive design patterns

- **TypeScript Violations:**
  - Never create new `.jsx` files - use `.tsx` with proper typing
  - Do not use `any` type except in extreme legacy scenarios
  - Never bypass TypeScript strict null checks
  - Do not create untyped component props or hook returns
  - Never use implicit `any` for API responses or complex objects

---

## 10. Periodic Review & Updating

- This guard rails document must be reviewed and updated at least quarterly, or after major product/technology shifts.
- All team members are responsible for compliance. Non-compliance may result in access restrictions or removal from the project.
- Document updates must reflect actual implementation details verified through code analysis.
- Major architectural changes must update both this document and the corresponding SSOT references.

---

## Appendix: Quick Reference

### Key Files for New Developers

**Backend Core:**
- [`backend/app/config.py`](backend/app/config.py) - Application configuration
- [`backend/app/database.py`](backend/app/database.py) - Database setup and session management
- [`backend/app/dependencies.py`](backend/app/dependencies.py) - FastAPI dependencies

**Frontend Core:**
- [`frontend/src/contexts/AuthContext.jsx`](frontend/src/contexts/AuthContext.jsx) - Authentication state
- [`frontend/src/stores/projectStore.js`](frontend/src/stores/projectStore.js) - Project state management
- [`frontend/src/api/client.js`](frontend/src/api/client.js) - HTTP client configuration

**Security & Middleware:**
- [`backend/app/auth/security.py`](backend/app/auth/security.py) - Security utilities
- [`backend/app/middleware/security.py`](backend/app/middleware/security.py) - Security middleware

**Chat System:**
- [`backend/app/services/chat_service.py`](backend/app/services/chat_service.py) - Chat business logic
- [`backend/app/websocket/manager.py`](backend/app/websocket/manager.py) - WebSocket management

### Development Commands

**Backend:**
```bash
# Database sync
python backend/sync_database.py

# Run migrations
cd backend && alembic upgrade head

# Start development server
cd backend && uvicorn app.main:app --reload
```

**Frontend:**
```bash
# Start development server
cd frontend && npm run dev

# Build for production
cd frontend && npm run build
```

**Docker:**
```bash
# Start full stack
docker-compose up --build

# Backend only
docker-compose up backend

# Frontend only
docker-compose up frontend
```

---
