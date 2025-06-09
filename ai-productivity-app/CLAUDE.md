# Developer Quick-Start ─ AI Productivity App

This short guide is aimed at **returning maintainers** who need to get back up-to-speed quickly.  It intentionally focuses on the *essentials*—where the code lives, how to run it, and which commands / environment variables you tend to forget.

> TL;DR:
> ```bash
> make install    # one-time, installs backend & frontend deps
> make dev        # start both services via docker-compose
> open http://localhost:5173  # React SPA (backend at :8000)
> ```

---

## 1. Repository layout

```
ai-productivity-app/
├── backend/            ← FastAPI service (Python 3.11+)
│   ├── app/            ← business logic & routers
│   ├── alembic/        ← db migrations
│   └── requirements.txt
├── frontend/           ← React 18 + Vite SPA
│   └── src/
├── docker-compose.yml  ← dev stack (backend + frontend)
├── docker-compose.prod.yml
├── Makefile            ← common task shortcuts
└── docs/               ← architecture & API docs (this file lives here)
```

Key backend sub-packages

• `app/main.py`        – creates FastAPI app, mounts routers, CORS & lifespan
• `app/config.py`      – pydantic-settings config (env-driven)
• `app/database.py`    – SQLAlchemy engine, `init_db()` helper
• `app/models/`        – declarative models (User, Project, Chat, …)
• `app/routers/`       – REST endpoints grouped by domain (`/api/auth`, `/api/projects`, …)

Frontend entry points

• `npm run dev` (inside *frontend*) – Vite dev server (port 5173)
• Production build lands in `frontend/dist` (served by nginx or similar)

---

## 2. Common dev commands

Command                  | Description
------------------------ | ----------------------------------------------
`make install`           | Install Python & Node dependencies
`make dev`               | docker-compose up – builds & starts stack (backend on 8000, frontend on 5173)
`make up / make down`    | Start/stop containers in background
`make logs`              | Tail combined compose logs
`make test`              | Run backend *pytest* and frontend *vitest*
`make lint`              | flake8 + mypy + eslint
`make format`            | black + prettier
`./start-local.sh`       | **No-Docker** workflow: local venv + Vite dev-server (handy when tweaking Python packages)

> Tip: The Makefile is your friend—`make help` prints a nice coloured list.

---

## 3. Environment variables you always forget

Variable                    | Default               | Notes
--------------------------- | --------------------- | -----------------------------------------------------------
`SECRET_KEY`                | "change-this…"        | Flask-style secret (JWT fallback)
`INSECURE_COOKIES`          | `true` (dev)          | Set to **false** in HTTPS prod so cookies get *Secure* flag
`DATABASE_URL`              | sqlite:///…/data/app.db | Point to Postgres in prod (`postgresql+psycopg2://…`)
`OPENAI_API_KEY`            | ―                     | Required for LLM calls (or use Azure vars below)
`AZURE_OPENAI_API_KEY`      | ―                     | If `llm_provider=azure`
`AZURE_OPENAI_ENDPOINT`     | ―                     | "https://<resource>.openai.azure.com"

`.env` at repo root will be auto-picked-up by `pydantic-settings`.

---

## 4. Database basics

SQLite is the default (file lives at `ai-productivity-app/data/app.db`).

### Create / reset
```bash
make db-reset    # drops & recreates DB using init_db()
```

### Migrations (Alembic)
```bash
cd backend
alembic upgrade head   # apply latest
alembic revision --autogenerate -m "<msg>"  # create new migration
```

Alembic env imports *all* models via `app.models.*` so make sure any new model lives there.

---

## 5. Running services individually

Backend only (without Docker):
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend only:
```bash
cd frontend
npm run dev  # → http://localhost:5173
```

Make sure `VITE_API_URL` in `.env` or shell points to your backend (default `http://localhost:8000`).

---

## 6. Test strategy

Backend: pytest + httpx (async) located in `backend/tests` – run with `make test`.

Frontend: vitest + testing-library/react – `npm test` or `make test`.

Coverage reports appear in console; backend also generates `.coverage` & `htmlcov/`.

---

## 7. Useful endpoints

- `GET /health`                       – simple liveness probe
- Swagger UI: `http://localhost:8000/docs`

Domain APIs (all prefixed with `/api`):

Endpoint group      | Purpose
------------------- | --------------------------------------------------
`/auth`             | JWT cookie login, logout, register, me, reset-pw
`/projects`         | CRUD + timeline, tags, search
`/chat`             | Chat sessions, messages, **WebSocket** at `/ws/sessions/{id}`
`/code`             | Repository ingestion & chunk listing (tree-sitter)
`/search`           | Semantic / keyword search (vector store, phase-4)

See `docs/API.md` for detailed JSON payloads.

---

## 8. Gotchas & pro-tips

1. **Cookie auth & HTTPS** – If running behind TLS *unset* `INSECURE_COOKIES` so the `Secure` flag is applied; otherwise browsers drop the cookie.
2. **IDE path confusion** – `app.config` builds an *absolute* SQLite URL so migrations & runtime point at the *same* file regardless of CWD.
3. **WebSockets** – Browsers automatically include the `access_token` cookie during the WS handshake; tests fall back to `?token=` query-param.
4. **Optional heavy deps** – Anything requiring *numpy* (e.g. embedding models) is imported lazily so core actions still work in skinny CI runners.

---

Happy hacking 🚀
