# Developer Quick-Start ─ AI Productivity App

This short guide is aimed at **returning maintainers** who need to get back up-to-speed quickly. It focuses on the essentials – where the code lives, how to run it, and which commands / env-vars you tend to forget.

> TL;DR
> ```bash
> make install   # install Python + Node deps (one-time)
> make dev       # docker-compose up – backend:8000 / frontend:5173
> # open the app → http://localhost:5173
> ```

---

## 1. Repo layout

```
ai-productivity-app/
├── backend/            ← FastAPI service (Python ≥3.11)
│   ├── app/            ← business logic & routers
│   ├── alembic/        ← DB migrations
│   └── requirements.txt
├── frontend/           ← React 18 + Vite SPA
│   └── src/
├── docker-compose.yml  ← dev stack (backend + frontend)
├── docker-compose.prod.yml
├── Makefile            ← common task shortcuts
└── docs/               ← architecture & API docs (this file lives here)
```

Backend highlights
• `app/main.py` – creates FastAPI app, mounts routers, adds CORS/lifespan.
• `app/config.py` – pydantic-settings config (env driven).
• `app/database.py` – SQLAlchemy engine + `init_db()` helper.
• `app/models/` – declarative models (User, Project, Chat, …).
• `app/routers/` – REST endpoints grouped by domain (auth, projects, chat…).

Frontend entry points
• `npm run dev` (inside *frontend*) – Vite dev server on :5173.
• Production build emitted to `frontend/dist`.

---

## 2. Common dev commands (Makefile)

Command                 | What it does
----------------------- | ----------------------------------------------
`make install`          | Install Python & Node dependencies.
`make dev`              | docker-compose up – hot-reload backend & vite.
`make up` / `make down` | Start/stop stack in background.
`make logs`             | Tail compose logs.
`make test`             | Run *pytest* + *vitest*.
`make lint`             | flake8 + mypy + eslint.
`make format`           | black + prettier.
`./start-local.sh`      | **No-Docker** workflow (local venv + vite).

Run `make help` anytime for a colourised list.

---

## 3. Environment variables to remember

Variable                  | Default                     | Notes
------------------------- | --------------------------- | ---------------------------------------------
`SECRET_KEY`              | "change-this…"              | Flask-style secret (JWT fallback).
`INSECURE_COOKIES`        | `true` (dev)                | Set *false* behind TLS to add `Secure` flag.
`DATABASE_URL`            | sqlite:///../data/app.db     | Point to Postgres in prod (`postgresql://…`).
`OPENAI_API_KEY`          | ―                           | Required for LLM calls (or use Azure vars).
`LLM_MODEL`               | `gpt-4`                      | Override to `gpt-3.5-turbo` if GPT-4 not enabled.
`AZURE_OPENAI_API_KEY`    | ―                           | Only if `llm_provider=azure`.
`AZURE_OPENAI_ENDPOINT`   | ―                           | e.g. `https://<resource>.openai.azure.com`.

Put them in a `.env` at the repo root; `pydantic-settings` auto-loads it.

---

## 4. Database cheat-sheet

SQLite by default (`data/app.db`).

```bash
make db-reset     # drop & recreate via init_db()

# Alembic
cd backend
alembic upgrade head                           # migrate
alembic revision --autogenerate -m "my change" # new migration
```

---

## 5. Running services individually (no Docker)

Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Frontend
```bash
cd frontend
npm run dev  # → http://localhost:5173
```

Ensure `VITE_API_URL` (env or `frontend/.env`) points to backend, default `http://localhost:8000`.

---

## 6. Test strategy

• Backend – `pytest` + `httpx`, lives in `backend/tests`.
• Frontend – `vitest` + `@testing-library/react`.

Run both with `make test`; coverage appears in console.

---

## 7. Useful endpoints

• Liveness: `GET /health`
• Swagger UI: `http://localhost:8000/docs`

API groups (all under `/api`): auth, projects, chat (plus `/ws/sessions/{id}`), code, search.

---

## 8. Gotchas & pro-tips

1. **Cookie auth vs HTTPS** – Browsers ignore cookies marked *Secure* on plain HTTP; leave `INSECURE_COOKIES=true` locally.
2. **Absolute SQLite path** – `app.config` builds an absolute URL so both Alembic and runtime share the same DB.
3. **WebSocket auth** – Cookie is automatically included; tests may fall back to `?token=` query param.
4. **Optional heavy deps** – Modules needing *numpy* (embeddings) import lazily to keep core lightweight.
5. **GPT-4 access denied (403)** – If logs show `model_not_found`, set `LLM_MODEL=gpt-3.5-turbo` or any model available to your org.

---

Happy hacking 🚀
