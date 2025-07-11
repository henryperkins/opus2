To update `guardrails.instructions.md` to reflect the current Single Sources of Truth (SSOT) in the application, you need to reference the actual implementation files for configuration, data models, business logic, state management, and other canonical sources. Here is a comprehensive list of all code in your workspace that is relevant to the SSOTs described in the guardrails document:

---

**Backend SSOTs**

- Application Configuration:
  - `ai-productivity-app/backend/app/config.py`

- Database Models (Authoritative Data Schema):
  - All model files in `ai-productivity-app/backend/app/models/`:
    - `user.py`, `project.py`, `session.py`, `chat.py`, `timeline.py`, `code.py`, `search_history.py`, `import_job.py`, `knowledge.py`, `feedback.py`, `prompt.py`, `document_version.py`, `embedding.py`, `api_keys.py`, `base.py`, `config.py`, `__init__.py`

- Core Business Logic and Validation:
  - All service layer modules in `ai-productivity-app/backend/app/services/`:
    - `project_service.py`, `chat_service.py`, plus others for analytics, knowledge, security, etc.

- Database Migrations:
  - All migration scripts in `ai-productivity-app/backend/alembic/versions/`

- Database Setup and Session Management:
  - `ai-productivity-app/backend/app/database.py`

- FastAPI Dependencies:
  - `ai-productivity-app/backend/app/dependencies.py`

- Security Utilities and Middleware:
  - `ai-productivity-app/backend/app/auth/security.py`
  - `ai-productivity-app/backend/app/middleware/security.py`

- WebSocket Management:
  - `ai-productivity-app/backend/app/websocket/manager.py`

- Chat System Logic:
  - `ai-productivity-app/backend/app/services/chat_service.py`
  - `ai-productivity-app/backend/app/chat/processor.py`
  - `ai-productivity-app/backend/app/chat/commands.py`
  - `ai-productivity-app/backend/app/chat/context_builder.py`

- LLM Client and Streaming:
  - `ai-productivity-app/backend/app/llm/client.py`
  - `ai-productivity-app/backend/app/llm/streaming.py`

---

**Frontend SSOTs**

- Global Data Fetching & Caching:
  - `ai-productivity-app/frontend/src/queryClient.js`

- State Management (Zustand Stores):
  - `ai-productivity-app/frontend/src/stores/projectStore.js`
  - `ai-productivity-app/frontend/src/stores/authStore.js`
  - `ai-productivity-app/frontend/src/stores/chatStore.js`

- Runtime Context:
  - `ai-productivity-app/frontend/src/contexts/AuthContext.jsx`

- Main Chat Interface:
  - `ai-productivity-app/frontend/src/pages/ProjectChatPage.jsx`

- Project Interaction Hooks:
  - `ai-productivity-app/frontend/src/hooks/useProjects.js`
  - `ai-productivity-app/frontend/src/hooks/useProject.js`
  - `ai-productivity-app/frontend/src/hooks/useProjectSearch.js`
  - `ai-productivity-app/frontend/src/hooks/useProjectTimeline.js`

- Chat Interaction Hooks:
  - `ai-productivity-app/frontend/src/hooks/useChat.js`
  - `ai-productivity-app/frontend/src/hooks/useWebSocketChannel.js`

- Knowledge and Search Hooks:
  - `ai-productivity-app/frontend/src/hooks/useCodeSearch.js`
  - `ai-productivity-app/frontend/src/hooks/useKnowledgeContext.js`

- Auth Hooks:
  - `ai-productivity-app/frontend/src/hooks/useAuth.js`

- AI/Model Hooks:
  - `ai-productivity-app/frontend/src/hooks/useModelSelect.js`
  - `ai-productivity-app/frontend/src/hooks/useCodeExecutor.js`

- Mobile-First Design System:
  - `ai-productivity-app/frontend/src/components/common/MobileBottomSheet.jsx`
  - `ai-productivity-app/frontend/src/hooks/useMediaQuery.js`

- Enhanced Chat Architecture:
  - All chat components in `ai-productivity-app/frontend/src/components/chat/`:
    - `EnhancedMessageRenderer.jsx`, `EnhancedCommandInput.jsx`, `StreamingMessage.jsx`, `CitationRenderer.jsx`, and others

- HTTP Client Configuration:
  - `ai-productivity-app/frontend/src/api/client.js`

---

**Global/Platform SSOTs**

- Environment and Secret Management:
  - `.env`, `.env.example`, `ai-productivity-app/backend/.env`, `ai-productivity-app/frontend/.env`
  - `Settings` class in `ai-productivity-app/backend/app/config.py`

- Database Schema and Migrations:
  - All Alembic migration scripts in `ai-productivity-app/backend/alembic/versions/`
  - Migration environment in `ai-productivity-app/backend/alembic/env.py`
  - Database path resolution in `Settings._DEFAULT_DB_PATH` in `ai-productivity-app/backend/app/config.py`

---

**Documentation SSOT**

- Team/Public Process/Architecture:
  - All markdown documents in `docs/`, especially:
    - `docs/GUARDRAILS.md`
    - `docs/ISSUE_REMEDIATION_PLAN.md`

---

**Testing SSOT**

- Backend Tests:
  - All test files in `ai-productivity-app/backend/tests/`

- Frontend Tests:
  - (Not listed in the file search, but typically in `frontend/src/__tests__/` or similar)

---

This list covers all files and modules that are referenced as SSOTs in your guardrails document and are present in your workspace. Use these files as the canonical sources when updating the guardrails documentation to ensure it accurately reflects the current implementation. If you need to see the contents of any specific file for more detail, you can request it directly.I'll analyze the current codebase and update the guardrails document to reflect the actual single sources of truth (SSOT) in the application.

## Solution

I need to update the guardrails document to accurately reflect the current state of the codebase, particularly focusing on:
1. Correcting file paths to match the actual structure
2. Updating references to reflect the implemented components and services
3. Ensuring all SSOT references are accurate and exist in the codebase
4. Adding missing critical services and patterns that are now part of the application

### [GUARDRAILS.md](vscode-remote://ssh-remote/home/azureuser/opus2/docs/GUARDRAILS.md)

Update the guardrails document to reflect the current actual implementation and structure of the application.

````markdown
# Guard Rails: AI Productivity App

This document outlines mandatory guard rails (constraints, standards, and best practices) for contributing to, deploying, and operating the AI Productivity App. Adhering to these guidelines is essential for maintaining security, stability, code quality, and user trust.

---

## Single Sources of Truth (SSOT)

The following are implementation-verified single sources of truth. All contributors MUST reference and update these concrete sources, as established in code, to avoid duplication, drift, or ambiguity in business logic, configuration, data, and application state.

### Backend SSOTs

- **Application Configuration**
  - [`Settings`](../ai-productivity-app/backend/app/config.py) class in [`backend/app/config.py`](../ai-productivity-app/backend/app/config.py):
    - Loads all runtime configuration for the backend from environment variables using Pydantic BaseSettings.
    - All environment-driven logic must derive from this class.
    - Any new config must be added as a field to `Settings` and documented in `.env.example`.
    - Handles absolute database path resolution to avoid CWD-dependent issues.
    - Global instance accessed via `settings = get_settings()`.

- **Database Models (Authoritative Data Schema)**
  - SQLAlchemy model classes in [`backend/app/models/`](../ai-productivity-app/backend/app/models/):
    - **Core Models**: [`User`](../ai-productivity-app/backend/app/models/user.py), [`Project`](../ai-productivity-app/backend/app/models/project.py), [`Session`](../ai-productivity-app/backend/app/models/session.py)
    - **Chat System**: [`ChatSession`](../ai-productivity-app/backend/app/models/chat.py), [`ChatMessage`](../ai-productivity-app/backend/app/models/chat.py)
    - **Project Features**: [`TimelineEvent`](../ai-productivity-app/backend/app/models/timeline.py)
    - **Code Analysis**: [`CodeDocument`](../ai-productivity-app/backend/app/models/code.py), [`CodeEmbedding`](../ai-productivity-app/backend/app/models/code.py)
    - **Knowledge Base**: [`KnowledgeEntry`](../ai-productivity-app/backend/app/models/knowledge.py), [`KnowledgeEmbedding`](../ai-productivity-app/backend/app/models/knowledge.py)
    - **Search**: [`SearchHistory`](../ai-productivity-app/backend/app/models/search_history.py)
    - **Background Jobs**: [`ImportJob`](../ai-productivity-app/backend/app/models/import_job.py)
    - **Configuration**: [`ModelConfiguration`](../ai-productivity-app/backend/app/models/config.py), [`RuntimeConfig`](../ai-productivity-app/backend/app/models/config.py)
    - **Feedback**: [`UserFeedback`](../ai-productivity-app/backend/app/models/feedback.py), [`FeedbackSummary`](../ai-productivity-app/backend/app/models/feedback.py)
    - **Prompts**: [`PromptTemplate`](../ai-productivity-app/backend/app/models/prompt.py)
    - These classes define the full canonical persisted data shape for all project entities.
    - Any database change must update both the ORM class and generate a corresponding migration in [`backend/alembic/versions/`](../ai-productivity-app/backend/alembic/versions/).

- **Core Business Logic and Validation**
  - Service layer modules in [`backend/app/services/`](../ai-productivity-app/backend/app/services/):
    - [`ProjectService`](../ai-productivity-app/backend/app/services/project_service.py): Project CRUD, timeline management, statistics
    - [`ChatService`](../ai-productivity-app/backend/app/services/chat_service.py): Chat session/message management, WebSocket broadcasting
    - [`KnowledgeService`](../ai-productivity-app/backend/app/services/knowledge_service.py): Knowledge base management and search
    - [`EmbeddingService`](../ai-productivity-app/backend/app/services/embedding_service.py): Vector embedding generation
    - [`PostgresVectorService`](../ai-productivity-app/backend/app/services/postgres_vector_service.py): pgvector-based similarity search
    - [`UnifiedConfigService`](../ai-productivity-app/backend/app/services/unified_config_service.py): Centralized configuration management
    - [`ImportService`](../ai-productivity-app/backend/app/services/import_service.py): Git repository import and indexing
  - Model-level validation with `@validates` decorators in all model classes
  - All business/process rules must reside here, not as duplicated frontend or adhoc logic.

- **Chat Processing Pipeline**
  - [`ChatProcessor`](../ai-productivity-app/backend/app/chat/processor.py): Main chat orchestration with AI interactions
  - [`ContextBuilder`](../ai-productivity-app/backend/app/chat/context_builder.py): Code and conversation context extraction
  - [`CommandRegistry`](../ai-productivity-app/backend/app/chat/commands.py): Slash command implementation and registry

### Frontend SSOTs

- **Global Data Fetching & Caching**
  - **TanStack Query `QueryClient` singleton** in [`frontend/src/queryClient.js`](../ai-productivity-app/frontend/src/queryClient.js):
    - Central source of truth for *all* remote data the browser knows about.
    - Provides caching, optimistic updates, de-duplication and refetch orchestration.
    - Components and hooks **must** obtain server data through `useQuery / useMutation` bound to this client – never via ad-hoc `axios` calls.

- **Hybrid State Management Architecture**
  - **Server State**: TanStack Query for all remote data and API interactions
  - **Client State**: Zustand stores for local application state:
    - [`useProjectStore`](../ai-productivity-app/frontend/src/stores/projectStore.js): Project data, filters, pagination, and state updates
    - [`useAuthStore`](../ai-productivity-app/frontend/src/stores/authStore.js): User preferences (theme, settings) and session metadata
    - [`useChatStore`](../ai-productivity-app/frontend/src/stores/chatStore.js): Chat-specific client state and UI preferences
  - **Runtime Context**: React Context for cross-cutting concerns:
    - [`AuthContext`](../ai-productivity-app/frontend/src/contexts/AuthContext.jsx): Authentication runtime state powered by TanStack Query (`useQuery(['me'])`)

- **Primary Chat Interface**
  - [`ProjectChatPage`](../ai-productivity-app/frontend/src/pages/ProjectChatPage.jsx): **Main chat interface**
    - Integrated code execution, knowledge base, and AI model selection
    - Mobile-first responsive design with bottom sheet integration
    - Enhanced message rendering with streaming support and citations
    - WebSocket-powered real-time communication

- **Project Interaction Hooks**
  - Custom hooks in [`frontend/src/hooks/`](../ai-productivity-app/frontend/src/hooks/):
    - [`useProject`](../ai-productivity-app/frontend/src/hooks/useProject.js), [`useProjects`](../ai-productivity-app/frontend/src/hooks/useProjects.js): Project management
    - [`useChat`](../ai-productivity-app/frontend/src/hooks/useChat.js): Chat interaction with WebSocket support
    - [`useWebSocket`](../ai-productivity-app/frontend/src/hooks/useWebSocket.js), [`useWebSocketChannel`](../ai-productivity-app/frontend/src/hooks/useWebSocketChannel.js): Real-time communication
    - [`useCodeSearch`](../ai-productivity-app/frontend/src/hooks/useCodeSearch.js): Code-specific search functionality
    - [`useKnowledgeContext`](../ai-productivity-app/frontend/src/hooks/useKnowledgeContext.js): Knowledge base integration
    - [`useAuth`](../ai-productivity-app/frontend/src/hooks/useAuth.js): Authentication utilities
    - [`useModelSelect`](../ai-productivity-app/frontend/src/hooks/useModelSelect.js): AI model selection and configuration
    - [`useCodeExecutor`](../ai-productivity-app/frontend/src/hooks/useCodeExecutor.js): Code execution pipeline

- **Chat Components Architecture**
  - [`ChatLayout`](../ai-productivity-app/frontend/src/components/chat/ChatLayout.jsx): Main chat container
  - [`EnhancedMessageRenderer`](../ai-productivity-app/frontend/src/components/chat/EnhancedMessageRenderer.jsx): Message formatting
  - [`EnhancedCommandInput`](../ai-productivity-app/frontend/src/components/chat/EnhancedCommandInput.jsx): Monaco editor integration
  - [`StreamingMessage`](../ai-productivity-app/frontend/src/components/chat/StreamingMessage.jsx): Real-time streaming
  - [`CitationRenderer`](../ai-productivity-app/frontend/src/components/chat/CitationRenderer.jsx): Source citations
  - [`KnowledgePanel`](../ai-productivity-app/frontend/src/components/chat/KnowledgePanel.jsx): Knowledge base UI

- **Mobile-First Design System**
  - [`MobileBottomSheet`](../ai-productivity-app/frontend/src/components/common/MobileBottomSheet.jsx): Advanced mobile UI with gesture support
  - [`useMediaQuery`](../ai-productivity-app/frontend/src/hooks/useMediaQuery.js): Responsive design helper
  - [`useResponsiveLayout`](../ai-productivity-app/frontend/src/hooks/useResponsiveLayout.js): Layout adaptation

### Global/Platform SSOTs

- **Environment and Secret Management**
  - Configuration values and secrets live in:
    - [`.env.example`](../ai-productivity-app/.env.example), [`backend/.env`](../ai-productivity-app/backend/.env), [`frontend/.env`](../ai-productivity-app/frontend/.env)
    - **Never** copy or partially duplicate these values in code or in documentation.
    - The `Settings` class in `backend/app/config.py` is the sole interface for accessing environment variables.

- **Database Schema and Migrations**
  - Alembic migrations in [`backend/alembic/versions/`](../ai-productivity-app/backend/alembic/versions/)
    - Latest migrations include pgvector support, user feedback system, model configurations
    - Migration naming convention: `XXX_description.py` (e.g., `013_populate_model_configurations.py`)
  - Migration environment in [`backend/alembic/env.py`](../ai-productivity-app/backend/alembic/env.py)
  - Database URL resolution handled centrally in `Settings` class

- **API Client Configuration**
  - Frontend HTTP client in [`frontend/src/api/client.js`](../ai-productivity-app/frontend/src/api/client.js):
    - Configured Axios instance with CSRF token handling
    - Automatic retry with exponential backoff
    - Global error interceptors for auth failures

### Documentation SSOT

- **Team/Public Process/Architecture**
  - This document: [`docs/GUARDRAILS.md`](GUARDRAILS.md)
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
  - **Python:** Follow [PEP8](https://www.python.org/dev/peps/pep-0008/) and enforce with `ruff` (configured in `pyproject.toml`).
  - **JavaScript/React:** ESLint configuration in `.eslintrc.json`.
- **Type Safety:**
  - Python type hints enforced, with Pydantic for API contracts.
  - Progressive TypeScript migration for frontend components.
- **Code Reviews:**
  - All code changes MUST be peer-reviewed via Pull Requests.
  - Automated linting and formatting checks must pass before merge.
- **Documentation:**
  - All public-facing functions, classes, and API endpoints must have docstrings or JSDoc.
  - Update and maintain docs for feature changes.

---

## 2. Security Practices

- **Secret Management:**
  - **Never commit secrets:** API keys, credentials, and private keys MUST NOT be committed to source control.
  - Use `.env.example` to document required env vars.
  - All secrets accessed through the `Settings` class configuration layer.
  - Secret scanning via [`secret_scanner`](../ai-productivity-app/backend/app/chat/secret_scanner.py) for chat messages.

- **Authentication & Authorization:**
  - JWT tokens with HttpOnly cookies for session management
  - Session tracking via [`Session`](../ai-productivity-app/backend/app/models/session.py) model with JTI (JWT ID) validation
  - Rate limiting: 5 attempts per minute per IP address on auth endpoints
  - Password hashing using bcrypt (via passlib)
  - Support for invite-code based registration when enabled

- **CSRF Protection:**
  - Double-submit cookie pattern with `csrftoken` cookie and `X-CSRFToken` header
  - CSRF validation enforced on all state-changing requests (POST, PUT, PATCH, DELETE)
  - Auth endpoints exempted from CSRF (rely on rate limiting instead)
  - Implementation in [`backend/app/auth/security.py`](../ai-productivity-app/backend/app/auth/security.py)

- **Security Headers:**
  - Implemented via [`SecurityHeadersMiddleware`](../ai-productivity-app/backend/app/middleware/security.py):
    - CSP (Content Security Policy) with strict directives
    - HSTS (HTTP Strict Transport Security)
    - X-Frame-Options: DENY
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: same-origin

- **WebSocket Security:**
  - JWT token validation required for all WebSocket connections
  - User authentication checked before processing any WebSocket messages
  - Connection lifecycle managed with proper cleanup via [`ConnectionManager`](../ai-productivity-app/backend/app/websocket/manager.py)

- **Content Filtering:**
  - [`ContentFilter`](../ai-productivity-app/backend/app/services/content_filter.py): Sensitive content detection and filtering
  - Applied to code chunks and chat messages before processing

- **Input Validation & Sanitization:**
  - All user-generated data validated via Pydantic schemas
  - SQLAlchemy model validators with `@validates` decorators
  - Chat message content validation and sanitization

---

## Critical Application Logic That Must Be Respected

The following application logic patterns and modules are essential for the correct, secure operation of the system:

### Backend (Python/FastAPI)

- **API Endpoint Contracts:**
  - All route definitions in [`backend/app/routers/`](../ai-productivity-app/backend/app/routers/) contain parameter validation, role enforcement, and error handling.

- **Authentication, Sessions, and Security:**
  - Token issuance and session management logic centralized in [`auth.py`](../ai-productivity-app/backend/app/routers/auth.py)
  - **SecurityHeadersMiddleware** enforces required security headers and CSRF validation
  - **Rate-limiting:** Via `limiter` instance in [`backend/app/auth/security.py`](../ai-productivity-app/backend/app/auth/security.py)

- **Permissions and Authentication Dependencies:**
  - Permission enforcement via [`dependencies.py`](../ai-productivity-app/backend/app/dependencies.py):
    - `CurrentUserRequired`: Enforces authentication
    - `CurrentUserOptional`: Provides user if authenticated
    - `DatabaseDep`: Provides SQLAlchemy session dependency

- **Business Logic — Service Layer:**
  - Service-layer modules in [`backend/app/services/`](../ai-productivity-app/backend/app/services/):
    - All database operations must go through service layer
    - Cross-entity business rules enforced at service level
    - Atomic operations via [`AtomicOperations`](../ai-productivity-app/backend/app/services/atomic_operations.py)

- **WebSocket Management:**
  - [`ConnectionManager`](../ai-productivity-app/backend/app/websocket/manager.py): Thread-safe connection lifecycle
  - Session-based grouping and user tracking
  - Automatic cleanup on disconnect

- **LLM Integration:**
  - [`LLMClient`](../ai-productivity-app/backend/app/llm/client.py): Provider-agnostic LLM interface
  - [`StreamingHandler`](../ai-productivity-app/backend/app/llm/streaming.py): Real-time streaming support
  - Tool/function calling support via [`tools`](../ai-productivity-app/backend/app/llm/tools.py)

### Frontend (React/JS)

- **Authentication and Access Gating:**
  - `useRequireAuth()` in [`useAuth.js`](../ai-productivity-app/frontend/src/hooks/useAuth.js) for protected pages
  - Dual auth state: `AuthContext` for runtime, `useAuthStore` for persistence

- **Data Loading and State Management:**
  - All API data through TanStack Query hooks
  - Client state through designated Zustand stores
  - Never bypass these patterns for direct API calls

- **HTTP Client Configuration:**
  - All API calls must use configured [`client`](../ai-productivity-app/frontend/src/api/client.js):
    - CSRF token attachment
    - HttpOnly cookie management
    - Automatic error handling

- **Chat System Architecture:**
  - [`ProjectChatPage`](../ai-productivity-app/frontend/src/pages/ProjectChatPage.jsx) as single chat UI source
  - Component hierarchy enforced through established patterns
  - WebSocket integration via dedicated hooks

### Cross-Cutting Security Patterns

- **Middleware Chain:**
  - Security, CSRF, and CORS middleware always active
  - Rate limiting on sensitive endpoints
  - No bypass allowed

- **Database Operations:**
  - All writes through validated service interfaces
  - Transaction management via service layer
  - No direct DB manipulation

- **Environment Configuration:**
  - Centralized through `Settings` class
  - Database paths use absolute resolution
  - CORS and cookie security configurable

---

## 3. Data Privacy & Usage

- **Personal Data:**
  - Minimal data collection principle
  - User data export capabilities via API
  - Soft-delete pattern for data retention

- **Logging:**
  - No secrets or PII in logs
  - Structured logging with appropriate levels
  - Audit trails for security events

- **Analytics:**
  - [`AnalyticsService`](../ai-productivity-app/backend/app/services/analytics_service.py): Privacy-respecting analytics
  - [`MetricsService`](../ai-productivity-app/backend/app/services/metrics_service.py): Performance tracking
  - Response quality tracking via [`useResponseQualityTracking`](../ai-productivity-app/frontend/src/hooks/useResponseQualityTracking.js)

---

## 4. Testing & Validation

- **Backend Testing:**
  - Comprehensive test suite in [`backend/tests/`](../ai-productivity-app/backend/tests/):
    - Authentication and security: `test_auth.py`, `test_security_headers.py`
    - Core features: `test_projects.py`, `test_chat.py`
    - Advanced features: `test_claude_thinking_phase5.py`, `test_postgres_vector_service.py`
    - Integration: `test_integration.py`, `test_feedback_integration.py`
  - Fixtures in [`conftest.py`](../ai-productivity-app/backend/tests/conftest.py)

- **Frontend Testing:**
  - Integration tests: [`chat.integration.test.js`](../ai-productivity-app/frontend/src/hooks/__tests__/chat.integration.test.js)
  - Component testing with React Testing Library
  - Mock API responses for isolation

- **Security Testing:**
  - CSRF protection: `test_auth.py`
  - Rate limiting: `test_auth.py`
  - Secret scanning: `test_secret_scanner.py`
  - Content filtering: `test_content_filtering.py`

---

## 5. Infrastructure & Deployment

- **Containerization:**
  - Docker Compose in [`docker-compose.yml`](../ai-productivity-app/docker-compose.yml)
  - Backend: Port 8000, health check at `/health/ready`
  - Frontend: Port 5173 with hot-reload
  - PostgreSQL with pgvector extension support

- **Database Management:**
  - Alembic migrations with proper versioning
  - Schema verification tools: `verify_schema.py`
  - Database sync utilities: `sync_database.py`

- **Environment Configuration:**
  - Development: `INSECURE_COOKIES=true`
  - Production: Secure cookies enforced
  - Provider-specific configs for LLM services

---

## 6. API & Integration

- **External APIs:**
  - LLM providers: OpenAI, Azure OpenAI, Anthropic
  - Embedding services via [`EmbeddingGenerator`](../ai-productivity-app/backend/app/embeddings/generator.py)
  - Git integration for repository import

- **Internal API Design:**
  - RESTful endpoints with consistent patterns
  - WebSocket for real-time features
  - Structured error responses

- **Rate Limiting:**
  - Auth endpoints: 5/minute/IP
  - Configurable via environment
  - Redis-backed in production

---

## 7. Contribution Process

- **Pull Requests:**
  - Must reference affected SSOTs
  - Include tests for new features
  - Update documentation

- **Code Style:**
  - Python: `ruff` formatting
  - JS/React: ESLint rules
  - Consistent naming conventions

---

## 8. Operational Guard Rails

- **Monitoring:**
  - Health endpoints for all services
  - Performance metrics collection
  - Error tracking and alerting

- **Data Management:**
  - Regular backups required
  - Migration rollback procedures
  - Data retention policies

---

## 9. Prohibited Practices

- **Security Violations:**
  - Never bypass authentication or authorization
  - No hardcoded secrets or credentials
  - Don't disable security middleware
  - Never expose internal errors to clients

- **Architecture Violations:**
  - Don't bypass service layer for DB operations
  - No direct database connections outside `DatabaseDep`
  - Don't bypass state management patterns
  - Never create separate HTTP clients without proper config

- **Development Practices:**
  - No untested code in production
  - Don't store business logic in migrations
  - Never mutate global state from UI
  - No ad-hoc configuration outside `Settings`

- **Chat System Violations:**
  - Don't bypass `ChatService` for messages
  - Never skip WebSocket authentication
  - Don't implement commands outside registry
  - No custom chat UIs outside established patterns

---

## 10. Periodic Review & Updating

- Quarterly review of this document
- Updates must reflect actual implementation
- Team compliance is mandatory
- Version control for all changes

---

## Appendix: Quick Reference

### Key Files for New Developers

**Backend Core:**
- [`backend/app/config.py`](../ai-productivity-app/backend/app/config.py) - Configuration
- [`backend/app/database.py`](../ai-productivity-app/backend/app/database.py) - Database setup
- [`backend/app/dependencies.py`](../ai-productivity-app/backend/app/dependencies.py) - Dependencies

**Frontend Core:**
- [`frontend/src/queryClient.js`](../ai-productivity-app/frontend/src/queryClient.js) - Data fetching
- [`frontend/src/stores/`](../ai-productivity-app/frontend/src/stores/) - State management
- [`frontend/src/api/client.js`](../ai-productivity-app/frontend/src/api/client.js) - API client

**Security:**
- [`backend/app/auth/security.py`](../ai-productivity-app/backend/app/auth/security.py) - Auth utilities
- [`backend/app/middleware/security.py`](../ai-productivity-app/backend/app/middleware/security.py) - Security middleware

**Chat System:**
- [`backend/app/chat/processor.py`](../ai-productivity-app/backend/app/chat/processor.py) - Chat orchestration
- [`backend/app/websocket/manager.py`](../ai-productivity-app/backend/app/websocket/manager.py) - WebSocket management

### Development Commands

**Backend:**
```bash
# Install dependencies
cd ai-productivity-app/backend && pip install -r requirements.txt

# Run migrations
cd ai-productivity-app/backend && alembic upgrade head

# Start development server
cd ai-productivity-app/backend && uvicorn app.main:app --reload
```

**Frontend:**
```bash
# Install dependencies
cd ai-productivity-app/frontend && npm install

# Start development server
cd ai-productivity-app/frontend && npm run dev

# Build for production
cd ai-productivity-app/frontend && npm run build
```

**Docker:**
```bash
# Start full stack
cd ai-productivity-app && docker compose up --build

# Backend only
cd ai-productivity-app && docker compose up backend

# Frontend only
cd ai-productivity-app && docker compose up frontend
```

---
````

Made changes.
