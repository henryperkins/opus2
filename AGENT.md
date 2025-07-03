# AGENT.md - AI Productivity App

## Build/Test Commands
- `make dev` - Start full development stack with Docker
- `make test` - Run all tests (backend pytest + frontend vitest)
- `make lint` - Run linters (flake8, mypy, eslint)
- `make format` - Format code (black, prettier)
- `make check` - Run lint + test (pre-commit checks)
- Single backend test: `cd backend && python -m pytest tests/test_specific.py::test_name -v`
- Single frontend test: `cd frontend && npm test -- --run test_name`
- Frontend test watch: `cd frontend && npm test`

## Architecture
- **Backend**: FastAPI + SQLAlchemy with models, services, routers structure
- **Frontend**: React 19 + Vite with pages, components, hooks, stores organization
- **Database**: PostgreSQL (production) / SQLite (dev) with Alembic migrations
- **State**: Zustand stores + React Query for server state
- **WebSocket**: Real-time chat via `/ws/sessions/{session_id}`

## Code Style
- **Backend**: Black formatting, flake8 linting, type hints required
- **Frontend**: Prettier formatting, ESLint, JSX components with PropTypes
- **Imports**: Standard → Third-party → Local (grouped with blank lines)
- **Error handling**: Custom exception hierarchy, structured logging
- **Components**: PascalCase exports, camelCase props, Tailwind CSS styling
