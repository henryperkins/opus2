# GUARDRAILS — Implementation & Code-Style Rules (Phases 1–3)

This document supplements the top-level `GUARDRAILS.md` by codifying the **file-naming conventions, extensions, and code-pattern requirements** that must be followed when implementing the three chat-experience phases described in the *Complete Integration Guide*:

1. **Phase 1 – Knowledge Base Integration**  
2. **Phase 2 – Model Configuration**  
3. **Phase 3 – Enhanced Response Rendering & Streaming**

It exists inside `docs/` so that developers who are browsing architectural / design docs see the same constraints that CI enforces at build time.

---

## 1. File-extension conventions

| Layer | Purpose | Mandatory extension | Notes |
|-------|---------|---------------------|-------|
| **Frontend (React)** | UI components using JSX/TSX | `.tsx` | All visual components **must** be typed. No plain `.jsx`.
| | Non-JSX helpers (utils, hooks, stores) | `.ts` | Hooks must start with `use`. No transitive state in utils.
| **Backend (FastAPI + Python 3.11+)** | Application source | `.py` | Use absolute imports rooted at `app.` namespace.
| **Database Migrations** | Alembic revisions | `<rev>_<slug>.py` | Auto-generated + hand-edited — keep `upgrade` / `downgrade` idempotent.
| **SQL Seeds** | Raw SQL fixtures | `.sql` | Only for deterministic seed data, not schema.
| **Documentation** | Markdown docs | `.md` | Keep within `docs/`; cross-link using relative paths.
| **Env samples** | Example env files | `.env.example` | Never commit real secrets.

Any deviation will be blocked by the *file-extension* pre-commit hook (`scripts/check_filenames.sh`).

---

## 2. Directory & naming rules for the three phases

### Phase 1 — Knowledge Base Integration

Frontend:
* Components live under `frontend/src/components/knowledge/` and are suffixed with **`…Panel.tsx`**, **`…Search.tsx`**, or **`…Assistant.tsx`** according to role.
* Knowledge-specific command handlers belong in `frontend/src/commands/knowledge-commands.ts`.

Backend:
* New routers must be placed in `backend/app/routers/search.py`.
* Heavy lifting (vector look-ups, hybrid search) goes in `backend/app/services/knowledge_service.py`.
* **Never** embed DB logic directly in the router; always call the service layer.

### Phase 2 — Model Configuration

Frontend:
* Settings-related UIs reside in `frontend/src/components/settings/`.
* `ModelSwitcher.tsx` is the single source of model selection inside the chat header; do **not** duplicate switchers elsewhere.

Backend:
* All model-pref endpoints live in `backend/app/routers/config.py`.
* Alembic revision adding `prompt_templates` and `user_model_preferences` **must** follow the naming pattern `YYYYMMDD_hhmm_add_prompt_and_prefs.py`.

### Phase 3 — Response Rendering

Frontend only:
* Stream & render logic lives in `frontend/src/components/chat/`.  
  – Incremental token handling → `StreamingMessage.tsx`  
  – Rich markdown / code / mermaid → `RichMessageRenderer.tsx`  
  – Interactive post-processing → `InteractiveElements.tsx`, `ResponseTransformer.tsx`
* Any new visualisation component that weighs > 10 kB gzipped **must** be lazy-loaded via `React.lazy`.

---

## 3. Coding patterns (lint-enforced)

1. **React**
   * Use function components + hooks only; no class components.
   * All props and state must be typed — `any` is forbidden. ESLint rule `@typescript-eslint/no-explicit-any` is in *error* mode.
   * Hooks **must** start with `use` and reside in `frontend/src/hooks/`.

2. **Python**
   * Routers: `@router.<method>(path)` with **dependency-injected** `db: Session = Depends(get_db)`; never `SessionLocal()` inside functions.
   * All pydantic models live in `backend/app/schemas/`; they are the only accepted request/response bodies.
   * Business logic must live in `services/`; routers may orchestrate but not compute.

3. **Streaming**
   * WebSocket events must use the envelope `{type, message_id, content?, done?}` — see `frontend/src/components/chat/StreamingMessage.tsx`.
   * `done` flag **must** be sent exactly once per message_id. Server violations are CI-tested via `tests/test_streaming_contract.py`.

---

## 4. CI / Pre-commit hooks that back these guardrails

* `black`, `ruff`, `isort` – Python formatting / lint.
* `eslint --max-warnings 0` – JS/TS lint.
* `scripts/check_filenames.sh` – validates file extensions and directory placement described above.
* `scripts/scan_secrets.sh` – blocks accidental secret leakage.

CI **will fail** if any of the above checks fail.  Developers should run `pre-commit install` locally.

---

## 5. Migration & versioning responsibilities

* Every backward-incompatible API change **must** bump the backend minor version in `backend/app/__init__.py` and add a note to `CHANGELOG.md`.
* Database migrations run automatically on container start-up; they **must** be idempotent and irreversible only when strictly necessary.

---

## 6. Contributing checklist (TL;DR)

1. Follow the file-extension table above.
2. Put logic in the correct layer (router → service → model).
3. Never bypass the *Single Sources of Truth* listed in the root `GUARDRAILS.md`.
4. Run `npm test && pytest` and ensure green.
5. Create a *draft* PR early; link to the corresponding SSOT sections that are touched.

If in doubt, ping the **#maintainers** channel before merging.
