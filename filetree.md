# Complete File Tree and Module Descriptions

## 📁 Project Structure

```
ai-productivity-app/
├── 📁 backend/
│   ├── 📁 app/
│   │   ├── 📄 __init__.py                 # Package initializer
│   │   ├── 📄 main.py                     # FastAPI application entry point
│   │   ├── 📄 config.py                   # Configuration and environment variables
│   │   ├── 📄 database.py                 # Database connection and session management
│   │   ├── 📄 dependencies.py             # Dependency injection utilities
│   │   │
│   │   ├── 📁 auth/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 security.py             # Password hashing, JWT tokens
│   │   │   ├── 📄 schemas.py              # Pydantic models for auth
│   │   │   └── 📄 utils.py                # Auth helper functions
│   │   │
│   │   ├── 📁 models/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py                 # SQLAlchemy base model
│   │   │   ├── 📄 user.py                 # User model
│   │   │   ├── 📄 project.py              # Project model
│   │   │   ├── 📄 chat.py                 # ChatSession, ChatMessage models
│   │   │   ├── 📄 code.py                 # CodeDocument, CodeEmbedding models
│   │   │   ├── 📄 timeline.py             # TimelineEvent model
│   │   │   └── 📄 api_keys.py             # APIKey model
│   │   │
│   │   ├── 📁 routers/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py                 # Authentication endpoints
│   │   │   ├── 📄 projects.py             # Project management endpoints
│   │   │   ├── 📄 chat.py                 # Chat session endpoints
│   │   │   ├── 📄 code.py                 # Code file management endpoints
│   │   │   ├── 📄 search.py               # Search endpoints
│   │   │   ├── 📄 config.py               # Configuration endpoints
│   │   │   └── 📄 monitoring.py           # Health check and metrics endpoints
│   │   │
│   │   ├── 📁 websocket/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 manager.py              # WebSocket connection management
│   │   │   └── 📄 handlers.py             # WebSocket message handlers
│   │   │
│   │   ├── 📁 code_processing/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 parser.py               # Tree-sitter code parser
│   │   │   ├── 📄 chunker.py              # Semantic code chunking
│   │   │   ├── 📄 language_detector.py    # File language detection
│   │   │   └── 📄 git_integration.py      # Git repository handling
│   │   │
│   │   ├── 📁 embeddings/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 generator.py            # Embedding generation with OpenAI
│   │   │   ├── 📄 cache.py                # Embedding cache management
│   │   │   └── 📄 batch_processor.py      # Batch embedding processing
│   │   │
│   │   ├── 📁 search/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 vector_store.py         # SQLite VSS implementation
│   │   │   ├── 📄 hybrid.py               # Hybrid search orchestration
│   │   │   ├── 📄 filters.py              # Search filter logic
│   │   │   └── 📄 ranker.py               # Result ranking algorithms
│   │   │
│   │   ├── 📁 chat/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 processor.py            # Chat message processing
│   │   │   ├── 📄 commands.py             # Slash command implementations
│   │   │   ├── 📄 context_builder.py      # Context extraction and building
│   │   │   └── 📄 secret_scanner.py       # Secret detection and redaction
│   │   │
│   │   ├── 📁 llm/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 client.py               # LLM client abstraction
│   │   │   ├── 📄 openai_provider.py      # OpenAI implementation
│   │   │   ├── 📄 azure_provider.py       # Azure OpenAI implementation
│   │   │   └── 📄 streaming.py            # Response streaming utilities
│   │   │
│   │   ├── 📁 utils/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 cache.py                # General caching utilities
│   │   │   ├── 📄 background_tasks.py     # Background task management
│   │   │   ├── 📄 validators.py           # Input validation utilities
│   │   │   └── 📄 file_utils.py           # File handling utilities
│   │   │
│   │   └── 📁 schemas/
│   │       ├── 📄 __init__.py
│   │       ├── 📄 user.py                 # User Pydantic schemas
│   │       ├── 📄 project.py              # Project Pydantic schemas
│   │       ├── 📄 chat.py                 # Chat Pydantic schemas
│   │       ├── 📄 code.py                 # Code Pydantic schemas
│   │       └── 📄 search.py               # Search Pydantic schemas
│   │
│   ├── 📁 alembic/
│   │   ├── 📄 alembic.ini                 # Alembic configuration
│   │   ├── 📄 env.py                      # Migration environment
│   │   ├── 📁 versions/                   # Database migrations
│   │   └── 📄 script.py.mako              # Migration template
│   │
│   ├── 📁 tests/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 conftest.py                 # Pytest fixtures
│   │   ├── 📄 test_auth.py                # Authentication tests
│   │   ├── 📄 test_projects.py            # Project management tests
│   │   ├── 📄 test_chat.py                # Chat functionality tests
│   │   ├── 📄 test_search.py              # Search tests
│   │   └── 📄 test_integration.py         # End-to-end tests
│   │
│   ├── 📁 scripts/
│   │   ├── 📄 setup_tree_sitter.py        # Tree-sitter grammar setup
│   │   ├── 📄 init_db.py                  # Database initialization
│   │   └── 📄 create_admin.py             # Create admin user script
│   │
│   ├── 📄 requirements.txt                # Python dependencies
│   ├── 📄 requirements-dev.txt            # Development dependencies
│   ├── 📄 Dockerfile                      # Backend Docker image
│   ├── 📄 .env.example                    # Environment variables template
│   └── 📄 pyproject.toml                  # Python project configuration
│
├── 📁 frontend/
│   ├── 📁 public/
│   │   └── 📄 favicon.ico                 # Application icon
│   │
│   ├── 📁 src/
│   │   ├── 📁 api/
│   │   │   ├── 📄 client.js               # API client setup
│   │   │   ├── 📄 auth.js                 # Authentication API calls
│   │   │   ├── 📄 projects.js             # Projects API calls
│   │   │   ├── 📄 chat.js                 # Chat API calls
│   │   │   └── 📄 search.js               # Search API calls
│   │   │
│   │   ├── 📁 components/
│   │   │   ├── 📁 auth/
│   │   │   │   ├── 📄 Login.jsx           # Login form component
│   │   │   │   ├── 📄 Register.jsx        # Registration form
│   │   │   │   └── 📄 UserProfile.jsx     # User profile management
│   │   │   │
│   │   │   ├── 📁 projects/
│   │   │   │   ├── 📄 ProjectCard.jsx     # Project card display
│   │   │   │   ├── 📄 ProjectForm.jsx     # Project creation/edit form
│   │   │   │   ├── 📄 Timeline.jsx        # Project timeline view
│   │   │   │   └── 📄 CreateProjectModal.jsx
│   │   │   │
│   │   │   ├── 📁 chat/
│   │   │   │   ├── 📄 CodeChat.jsx        # Main chat interface
│   │   │   │   ├── 📄 MessageList.jsx     # Chat message display
│   │   │   │   ├── 📄 CommandInput.jsx    # Command-aware input
│   │   │   │   └── 📄 CodePreview.jsx     # Code snippet preview
│   │   │   │
│   │   │   ├── 📁 editor/
│   │   │   │   ├── 📄 MonacoEditor.jsx    # Monaco editor wrapper
│   │   │   │   ├── 📄 DiffView.jsx        # Code diff display
│   │   │   │   └── 📄 LanguageSelector.jsx
│   │   │   │
│   │   │   ├── 📁 search/
│   │   │   │   ├── 📄 SearchBar.jsx       # Search input with suggestions
│   │   │   │   ├── 📄 SearchResults.jsx   # Search results display
│   │   │   │   ├── 📄 SearchFilters.jsx   # Filter controls
│   │   │   │   └── 📄 CodeSnippet.jsx     # Code result preview
│   │   │   │
│   │   │   ├── 📁 common/
│   │   │   │   ├── 📄 Layout.jsx          # Main application layout
│   │   │   │   ├── 📄 Sidebar.jsx         # Navigation sidebar
│   │   │   │   ├── 📄 Header.jsx          # Application header
│   │   │   │   ├── 📄 Modal.jsx           # Reusable modal component
│   │   │   │   └── 📄 Toast.jsx           # Notification toasts
│   │   │   │
│   │   │   └── 📁 knowledge/
│   │   │       ├── 📄 FileUpload.jsx      # File upload interface
│   │   │       ├── 📄 RepositoryConnect.jsx # Git repo connection
│   │   │       └── 📄 DependencyGraph.jsx # Code dependency visualization
│   │   │
│   │   ├── 📁 hooks/
│   │   │   ├── 📄 useAuth.js              # Authentication hook
│   │   │   ├── 📄 useWebSocket.js         # WebSocket connection hook
│   │   │   ├── 📄 useDebounce.js          # Debouncing hook
│   │   │   └── 📄 usePersistentState.js   # Local storage state
│   │   │
│   │   ├── 📁 pages/
│   │   │   ├── 📄 Dashboard.jsx           # Main dashboard page
│   │   │   ├── 📄 ProjectPage.jsx         # Individual project page
│   │   │   ├── 📄 ChatPage.jsx            # Chat session page
│   │   │   ├── 📄 SearchPage.jsx          # Search interface page
│   │   │   └── 📄 SettingsPage.jsx        # Settings and config page
│   │   │
│   │   ├── 📁 utils/
│   │   │   ├── 📄 formatters.js           # Data formatting utilities
│   │   │   ├── 📄 validators.js           # Input validation
│   │   │   └── 📄 highlighter.js          # Syntax highlighting utils
│   │   │
│   │   ├── 📁 stores/
│   │   │   ├── 📄 authStore.js            # Authentication state
│   │   │   ├── 📄 projectStore.js         # Project state management
│   │   │   └── 📄 chatStore.js            # Chat state management
│   │   │
│   │   ├── 📁 styles/
│   │   │   ├── 📄 globals.css             # Global styles
│   │   │   └── 📄 tailwind.css            # Tailwind CSS imports
│   │   │
│   │   ├── 📄 App.jsx                     # Root application component
│   │   ├── 📄 main.jsx                    # Application entry point
│   │   └── 📄 router.jsx                  # React Router configuration
│   │
│   ├── 📄 package.json                    # Node.js dependencies
│   ├── 📄 vite.config.js                  # Vite configuration
│   ├── 📄 tailwind.config.js              # Tailwind CSS configuration
│   ├── 📄 postcss.config.js               # PostCSS configuration
│   ├── 📄 jsconfig.json                   # JavaScript configuration
│   ├── 📄 .eslintrc.js                    # ESLint configuration
│   └── 📄 Dockerfile                      # Frontend Docker image
│
├── 📁 docker/
│   ├── 📁 nginx/
│   │   ├── 📄 nginx.conf                  # Nginx configuration
│   │   └── 📄 ssl.conf                    # SSL configuration
│   │
│   └── 📁 scripts/
│       ├── 📄 backup.sh                   # Database backup script
│       └── 📄 restore.sh                  # Database restore script
│
├── 📁 docs/
│   ├── 📄 README.md                       # Project documentation
│   ├── 📄 SETUP.md                        # Setup instructions
│   ├── 📄 API.md                          # API documentation
│   ├── 📄 COMMANDS.md                     # Slash commands guide
│   └── 📄 DEPLOYMENT.md                   # Deployment guide
│
├── 📄 docker-compose.yml                  # Docker Compose configuration
├── 📄 docker-compose.prod.yml             # Production Docker Compose
├── 📄 .gitignore                          # Git ignore file
├── 📄 .env.example                        # Environment variables template
└── 📄 Makefile                           # Build and deployment commands
```

## 📋 Module Descriptions

### Backend Modules

#### Core Modules

**`app/main.py`**
- FastAPI application initialization
- Middleware configuration (CORS, security)
- Router registration
- WebSocket endpoints
- Startup/shutdown events

**`app/config.py`**
```python
# Manages all configuration from environment variables
# Includes settings for database, API keys, security, and feature flags
```

**`app/database.py`**
- SQLAlchemy engine creation
- Session factory configuration
- Database initialization routines
- Connection pool management

#### Authentication & Security

**`app/auth/security.py`**
- Password hashing with bcrypt
- JWT token creation and validation
- Session management utilities
- CSRF protection helpers

#### Data Models

**`app/models/`**
- **user.py**: User accounts, authentication data
- **project.py**: Project metadata, status tracking
- **chat.py**: Chat sessions and messages with code awareness
- **code.py**: Code documents, parsed symbols, embeddings
- **timeline.py**: Project activity timeline events

#### API Routers

**`app/routers/`**
- **auth.py**: Login, logout, registration, password reset
- **projects.py**: CRUD operations for projects, timeline events
- **chat.py**: Chat session management, message history
- **code.py**: File upload, repository sync, code indexing
- **search.py**: Unified search across code and chat
- **monitoring.py**: Health checks, metrics, API usage stats

#### Code Processing

**`app/code_processing/`**
- **parser.py**: Tree-sitter integration for AST parsing
- **chunker.py**: Intelligent code splitting for embeddings
- **language_detector.py**: File extension and content-based detection
- **git_integration.py**: Clone, pull, diff operations

#### Embeddings & Vector Search

**`app/embeddings/`**
- **generator.py**: OpenAI embeddings API integration
- **cache.py**: LRU cache for frequently used embeddings
- **batch_processor.py**: Efficient batch embedding generation

**`app/search/`**
- **vector_store.py**: SQLite VSS integration
- **hybrid.py**: Combines semantic, keyword, and structural search
- **ranker.py**: Result scoring and merging algorithms

#### Chat & LLM Integration

**`app/chat/`**
- **processor.py**: Message parsing, context extraction
- **commands.py**: Slash command implementations (/explain, /generate-tests, etc.)
- **context_builder.py**: Builds relevant context from codebase
- **secret_scanner.py**: Prevents API keys and secrets from being sent to LLM

**`app/llm/`**
- **client.py**: Abstract LLM interface
- **openai_provider.py**: OpenAI API implementation
- **azure_provider.py**: Azure OpenAI implementation
- **streaming.py**: Server-sent events for response streaming

#### WebSocket Management

**`app/websocket/`**
- **manager.py**: Connection pool management
- **handlers.py**: Message routing and broadcasting

### Frontend Modules

#### Core Application

**`src/App.jsx`**
- Root component with providers
- Global error boundaries
- Authentication wrapper

**`src/router.jsx`**
- React Router configuration
- Protected routes
- Layout nesting

#### API Integration

**`src/api/`**
- **client.js**: Axios instance with interceptors
- **auth.js**: Authentication API calls
- **projects.js**: Project management APIs
- **chat.js**: Chat and WebSocket setup
- **search.js**: Search API integration

#### Component Libraries

**`src/components/`**

**Auth Components**
- Login/Register forms with validation
- Profile management interface
- Session management

**Project Components**
- Project cards with status badges
- Timeline visualization
- Tag and emoji selectors

**Chat Components**
- Split-pane chat/code interface
- Message rendering with code highlighting
- Command palette with autocomplete
- File reference detection

**Editor Components**
- Monaco editor with custom themes
- Language detection and switching
- Diff view for code changes
- Minimap and outline support

**Search Components**
- Unified search bar with debouncing
- Filter sidebar
- Result previews with highlighting
- Jump-to-definition support

#### State Management

**`src/stores/`**
- **authStore.js**: User authentication state
- **projectStore.js**: Active projects and metadata
- **chatStore.js**: Chat sessions and messages

#### Custom Hooks

**`src/hooks/`**
- **useAuth.js**: Authentication status and methods
- **useWebSocket.js**: WebSocket connection management
- **useDebounce.js**: Input debouncing for search
- **usePersistentState.js**: LocalStorage-backed state

### Deployment & Infrastructure

**Docker Configuration**
- Multi-stage builds for minimal image size
- Health checks for all services
- Volume management for data persistence
- Network isolation between services

**Nginx Configuration**
- Reverse proxy for API and frontend
- SSL termination
- Gzip compression
- Cache headers for static assets

**Database Migrations**
- Alembic for schema versioning
- Automatic migration on startup
- Rollback capabilities

### Testing

**Backend Tests**
- Unit tests for business logic
- Integration tests for API endpoints
- WebSocket connection tests
- Search accuracy tests

**Frontend Tests**
- Component unit tests
- Integration tests for user flows
- E2E tests with Playwright

### Documentation

**User Guides**
- Setup instructions for local development
- Deployment guide for production
- Slash command reference
- API documentation with examples

This structure provides a complete, production-ready AI productivity application optimized for a small team, with clear separation of concerns and room for future enhancements.