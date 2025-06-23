# Backend Hardening Checklist

This living document tracks every gap identified in the security / reliability audit and the concrete action-items required to close it.  **Each PR must reference at least one checklist item and update the *Status* column when done.**

Legend
------
* **P0** – must be fixed _before production GA_
* **P1** – high priority, fix within next sprint
* **P2/P3** – medium / low

| Ref | Area | Task | DoD (definition-of-done) | Priority | Owner | Status |
|-----|------|------|--------------------------|----------|-------|--------|
| 1-A | Rate limiting | Replace in-memory bucket with Redis + re-enable `@limiter.limit` decorators | 5 failed login attempts from two separate uvicorn workers yield HTTP 429 | P0 | Security | 🔲 |
| 1-B | Path validation | `CodeDocument.validate_file_path()` ensures `..` traversal cannot escape `UPLOAD_ROOT` | Uploads containing `../` rejected with error_code `PATH_NOT_ALLOWED` | P0 | Security | 🔲 |
| 1-C | Auth error taxonomy | Include `error_code` (`BAD_CREDENTIALS`, `INACTIVE_ACCOUNT`) in `/login` responses; front-end shows correct message | Cypress test displays separate banners | P0 | Security | 🔲 |
| 2-A | Correlation IDs | Add `asgi-correlation-id` middleware and include `request_id` in all log records & websocket payloads | End-to-end request & WS events share same ID in logs | P1 | Backend | 🔲 |
| 2-B | Readiness probe | `/health/ready` checks DB, Redis, OpenAI and background-worker heartbeat; returns 503 on failure | K8s marks pod **Un-Ready** when Redis down | P1 | Platform | 🔲 |
| 2-C | WebSocket task cleanup | Track tasks per connection, cancel on disconnect to avoid leaks | Locust simulation shows 0 leaked tasks after 1 k connect/disconnect cycles | P1 | Backend | ✅ |
| 3-A | DB transactions | Use `async with session.begin()` for multi-step operations (import & others) | Killing worker mid-flow leaves DB consistent | P2 | Backend | ✅ |
| 3-B | Exception scope | Replace broad `except Exception` in `llm/client.py` with explicit errors, integrate Sentry | `pylint --disable=broad-except` passes | P2 | Backend | ✅ |
| 4-A | Rendering micro-service | Swap mock renderer for external `render-svc` (feature-flag fallback) | Markdown with ```python``` returns highlighted HTML | P2 | Feature | ✅ |
| 4-B | Knowledge base | Integrate Qdrant search / context builder; drop placeholders | `/api/knowledge/search` returns real vector results | P2 | Feature | ✅ |
| 5-A | Module size | Split big routers (`auth`, `code`) into smaller files; remove `sys.modules` hacks | No router > 400 LOC | P3 | Backend | 🔲 |
| 5-B | API versioning | Serve all routes under `/api/v1/*`; deprecate un-versioned | Swagger only shows `/api/v1` | P3 | Platform | 🔲 |
| 5-C | Migrations as source of truth | App start-up runs `alembic upgrade head`; delete `sync_database.py` | Deploy fails if migration missing | P3 | Platform | 🔲 |
| 6-A | DB indexes | Add composite indexes for frequent queries (search, file-list) | p95 filename search < 50 ms on 1 M rows | P3 | DBA | 🔲 |
| 6-B | Durable background queue | Move BackgroundTasks to Dramatiq + Redis with retry & admin UI | Job resumes after worker crash; `/admin/jobs` lists state | P4 | Platform | 🔲 |

How to update
-------------
1. In your PR description, reference the **Ref** code (e.g. “Closes 1-B”).
2. In this file, change the **Status** from 🔲 to ✅ and, optionally, add PR link.
3. Keep entries sorted by Ref.

> _Maintainers_: please keep this checklist concise. Finished items can be collapsed into an “Archive” section once shipped to production.

-------------------------------------------------------------------------------
Remediation Play-Book
-------------------------------------------------------------------------------

The following sections give **step-by-step instructions** for each checklist item so that any contributor can pick it up without additional context.  Every section follows the same template:

• Overview – why this matters.
• Implementation steps – code, infra, config.
• Testing – unit / integration / e2e.
• Roll-back – how to disable safely if something goes wrong.
• Docs / ops – files or run-books that must be updated.

---

### 1-A  Distributed Rate Limiting

**Overview**
The current in-memory token bucket works only inside a single process.  When we scale to >1 uvicorn worker (or to multiple pods) attackers can round-robin their requests and bypass limits.  Redis gives us a central store with atomic `INCR` + TTL operations.

**Implementation**
1. Add `redis` service to `docker-compose.yml` (5 MB Alpine image).
2. Create `app/utils/redis_client.py` that exports a lazily-initialised `aioredis.Redis` instance.
3. New helper `def enforce_redis_rate_limit(key, limit, window)` that executes:
   ```python
   async with redis.pipeline() as pipe:
       await pipe.incr(key)
       await pipe.expire(key, window, nx=True)
       count, _ = await pipe.execute()
       if count > limit: raise HTTPException(429, ...)
   ```
4. Replace calls to `enforce_rate_limit()` in `routers/auth.py`.
5. Re-enable Dormant SlowAPI decorators (`@limiter.limit`).  Keep a `settings.DISABLE_RATE_LIMITER` flag so unit tests can opt-out.
6. Remove the old in-memory map once all tests pass.

**Testing**
• Unit: pytest `tests/test_rate_limit.py` spins local redis and asserts that 6th request → 429.
• Integration: run two uvicorn workers behind nginx; curl 3× to each, expect 429 on 6th.
• Security: ZAP active scan for brute-force yields “Low”.

**Roll-back**
Set env `DISABLE_RATE_LIMITER=true` – code will fall back to old bucket (still imported for one release).  Remove flag in next major.

**Docs / Ops**
• `docs/OPERATIONS.md` – add redis port, memory requirements.
• Update Helm chart with an optional external redis URL.

---

### 1-B  Upload Path Validation

**Overview**
Attackers can craft `../../../etc/passwd` filenames to overwrite or read files after the background parser writes to disk.

**Implementation**
1. Define `UPLOAD_ROOT = Path(settings.upload_root).resolve()` in `config.py`.
2. In `CodeDocument.validate_file_path()` add:
   ```python
   p = (UPLOAD_ROOT / file_path).resolve()
   if not str(p).startswith(str(UPLOAD_ROOT)):
       raise ValueError("PATH_NOT_ALLOWED")
   ```
3. Normalise path with `PurePosixPath(file_path).as_posix()` to keep slashes consistent.
4. Block windows drive letters (`C:`) via regex.

**Testing**
• Pytest parametrised list of bad paths (`../..`, `..%2Fsecret`).
• Upload good file succeeds.
• Coverage target ≥ 90 % for validator.

**Roll-back**
Set `settings.upload_path_validation = "warn"` to only log until frontend is updated.

---

### 1-C  Authentication Error Taxonomy

**Overview**
Clients need to distinguish between “wrong password” vs “inactive account” for UX, while still preventing user enumeration.

**Implementation**
1. Create `app/schemas/errors.py` with enum:
   ```python
   class AuthError(str, Enum):
       BAD_CREDENTIALS = "BAD_CREDENTIALS"
       INACTIVE_ACCOUNT = "INACTIVE_ACCOUNT"
   ```
2. Modify `/login` handler:
   ```python
   raise HTTPException(401, detail="Invalid credentials", headers={"X-Error-Code": AuthError.BAD_CREDENTIALS})
   ```
3. Add Pydantic `ErrorResponse` model `{ error_code: str; message: str }` and use across routers.

**Testing**
• Cypress: inactive account → banner “Please verify email”.
• Attempt 10 random usernames → all return same latency to avoid timing leaks.

**Roll-back**
None needed – older clients will ignore the new header / JSON field.

---

*( sections 2-A … 6-B follow the same expanded template; truncated here for brevity – keep adding as items move from table to “in-progress” )*

---

### 2-A  Correlation IDs

**Overview**
Without correlation IDs it is impossible to trace a request across HTTP logs, background workers and WebSocket pushes.  This impairs debugging and security forensics.

**Implementation**
1. `poetry add asgi-correlation-id` (already lightweight).
2. In `app/main.py` add `CorrelationIdMiddleware` at the top of the stack with header name `X-Request-ID`.
3. Extend `logging.dictConfig` formatter: `'%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s'`.
4. Export helper `get_request_id()` via `contextvars`.  Use it inside `websocket/notify_manager.py` to add the ID to every payload: `{..., "request_id": get_request_id()}`.
5. Update frontend WebSocket listener to ignore / log this field.

**Testing**
• Unit: HTTP request returns header `X-Request-ID` and same value appears in log capture.
• Integration: start a chat -> follow trace from REST -> background Embeddings worker -> WS push, IDs match.
• Chaos: Force task exception, Sentry event includes request_id tag.

**Roll-back**
Set env `DISABLE_CORRELATION_ID=true` (handled in middleware init).

**Docs / Ops**
Document log format change and advise ELK / Datadog parsers to extract `request_id`.

---

### 2-B  Extended Readiness Probe

**Overview**
Only DB connectivity is checked today.  If Redis, OpenAI or background workers fail, Kubernetes continues to route traffic.

**Implementation**
1. Inject redis via `app.utils.redis_client`.
2. In `routers/monitoring.readiness_check()` perform:
   ```python
   try: await redis.ping(); checks["redis"] = "ready"
   except Exception as exc: checks["redis"] = f"error: {exc}"; not_ready=True
   ```
3. Azure/OpenAI: skip in CI → use `if not settings.skip_openai_health:` guard. Hit `/models` with 0.5-s timeout.
4. Background workers: each worker updates Redis key `worker:<pid>` every 30 s; readiness aggregates `keys("worker:*")` modified < 45 s.

**Testing**
• Unit mocks failing redis, expects 503 + redis error.
• Staging: scale workers to 2, kill one, readiness stays green. Kill both → readiness 503.

**Roll-back**
Set env `HEALTH_MIN_COMPONENTS=db` which bypasses extra checks.

**Docs / Ops**
Update Helm probe timeouts, add Grafana panel for component states.

---

### 2-C  WebSocket Task Cleanup

**Overview**
Each `notify_manager.send()` spawns fire-and-forget tasks; on disconnect they keep running and may hold DB conns.

**Implementation**
1. In `notify_manager` create `_tasks: dict[int, set[asyncio.Task]]`.
2. Replace `asyncio.create_task()` with helper `spawn(user_id, coro)` that registers the task and adds `add_done_callback(...)` removing itself.
3. On `disconnect()` iterate and `task.cancel()` then `await asyncio.gather(*tasks, return_exceptions=True)`.

**Testing**
Locust script: 100 users connect/disconnect 100 ×; assert `len(asyncio.all_tasks())` stabilises.

**Roll-back**
Fallback to current simple send by setting `settings.ws_task_tracking = false`.

**Docs / Ops**
Add note to troubleshooting guide: “Stuck tasks” alert refers to this mechanism.

---

### 3-A  Robust DB Transactions

**Overview**
Multiple `db.commit()` calls scatter logic; partial failures leave inconsistent state.

**Implementation**
1. Switch to SQLAlchemy 2 style `async_sessionmaker` (already imported).
2. Wrap multi-step routes/services in:
   ```python
   async with db.begin():
       ... # all writes
   ```
3. For background jobs create local session via `async_sessionmaker()` and same pattern.
4. Provide helper `atomic()` context to reduce code churn.

**Testing**
• Insert breakpoint/exception between two writes; assert both rolled back.
• pytest `pytest --maxfail=1 tests/db/test_atomic.py`.

**Roll-back**
Set env `ATOMIC_TRANSACTIONS=false` to restore commit-per-write (temporary).

**Docs / Ops**
Upgrade guide: mention need to call `session.rollback()` is now rare.

---

### 3-B  Narrow Exception Handling & Sentry

**Overview**
Broad `except Exception` hides bugs and hampers monitoring.

**Implementation**
1. `poetry add sentry-sdk[asyncio]`.  Initialise in `main.py` with DSN from env.
2. In `llm/client.py`:
   • Replace broad catches with `(httpx.HTTPError, TimeoutError, OpenAIError)`.
   • Unknown exceptions bubble up to FastAPI which Sentry captures.

**Testing**
• Simulate timeout; ensure retry executes.
• Inject ValueError; Sentry event appears in project.

**Roll-back**
Set `SENTRY_DSN=""` to disable capture.

**Docs / Ops**
Add “Debugging production failures” doc referencing Sentry.

---

### 4-A  Rendering Micro-service

**Overview**
Complex rendering (syntax highlight, math, diagrams) should not block API latency; move to dedicated service.

**Implementation**
1. Scaffold repo `render-svc` (FastAPI, pygments, mermaid-cli).
2. Add Kubernetes service & deployment.
3. In `routers/rendering.py` if `settings.render_endpoint` present: forward request with `httpx.AsyncClient.post()`.
4. Circuit-breaker using `tenacity`: fallback to local mock after 3 failures.

**Testing**
• Unit mocks remote 200, 500; assert fallback path.
• k6 load: 100 rps → p95 latency < 150 ms.

**Roll-back**
Unset `render_endpoint`; router uses existing placeholder.

**Docs / Ops**
Update architecture diagram; add helm charts for render-svc.

---

### 4-B  Knowledge Base with Qdrant

**Overview**
Hard-coded responses block true semantic search.

**Implementation**
1. Spin Qdrant container (`docker-compose.qdrant.yml`).
2. Create `services/embedding_service.py` with `create_index_if_missing()`, `upsert()` and `search()`.
3. At startup, ensure collection `kb_entries` exists with HNSW index.
4. Replace `/search` endpoint: embed query via OpenAI → search qdrant.
5. `/context` glues top-k results, honours `max_context_length`.

**Testing**
• pytest with local qdrant; insert dummy embeddings and search.
• Perf: search < 50 ms for 100 k vectors.

**Roll-back**
Env `USE_MOCK_KB=true` → original mock remains.

**Docs / Ops**
Add run-book “Rebuilding KB indices”.

---

### 5-A  Split Large Router Modules

**Overview**
Monolithic files hinder readability and cause circular import hacks.

**Implementation**
1. Create package `routers/auth/` with sub-routers: `registration.py`, `login.py`, `profile.py` etc.
2. Add `routers/__init__.py` that imports and attaches them to main FastAPI.
3. Move shared helpers to `services/auth_service.py`.
4. Remove `sys.modules` aliasing from models.

**Testing**
• `pytest -q` passes.
• `vulture` shows no dead imports.

**Roll-back**
Keep old `routers/auth.py` re-exporting routes for one release then delete.

**Docs / Ops**
Internal contribution guide updated with new structure.

---

### 5-B  API Versioning

**Overview**
Version prefix protects consumers from breaking changes.

**Implementation**
1. Create sub-app `app_v1 = FastAPI()`; mount under main app with `app.mount("/api/v1", app_v1)`.
2. Move all current routers to sub-app; add deprecation banner on old paths using `@deprecated`.
3. Configure OpenAPI: `openapi_url="/api/v1/openapi.json"`.

**Testing**
• Postman collection switched to v1.
• Old path returns 301 then 410 after two releases.

**Roll-back**
Keep both mounts temporarily.

**Docs / Ops**
Changelog with migration steps for SDK users.

---

### 5-C  Migrations as Single Source of Truth

**Overview**
`sync_database.py` bypasses Alembic creating drift.

**Implementation**
1. Delete `sync_database.py` and any `create_all()` calls in startup.
2. Entry-point runs:
   ```bash
   alembic upgrade head || exit 1
   ```
3. GitHub Action enforces `poetry run alembic upgrade --sql` dry-run to detect missing migrations.

**Testing**
• Schema diff test passes (alembic vs models).
• Downgrade then upgrade works.

**Roll-back**
Re-enable `create_all()` behind `ALLOW_SYNC_DB=true` (dev-only).

**Docs / Ops**
Add “DB migrations” SOP.

---

### 6-A  Database Index Optimisation

**Overview**
Filename search & history queries slow down with large data sets.

**Implementation**
1. Alembic migration:
   ```python
   op.create_index("idx_code_docs_project_path", "code_documents", ["project_id", "file_path"], postgresql_using="btree")
   ```
2. For search history: composite `(user_id, created_at DESC)`.

**Testing**
• pgbench before/after shows 5× speed-up.
• unit test uses sqlite → skip via dialect check.

**Roll-back**
`alembic downgrade -1`.

**Docs / Ops**
Add grafana panel “Slow queries (>200 ms)”.

---

### 6-B  Durable Background Queue

**Overview**
BackgroundTasks are ephemeral; a pod restart loses work.  Dramatiq + Redis supports retries and monitoring.

**Implementation**
1. `poetry add dramatiq[binaries]`.
2. Create `tasks.py` declaring `@dramatiq.actor(retries=3, max_retries=3, backoff=dramatiq.backoff.exponential)`.
3. Replace FastAPI BackgroundTasks with `tasks.process_code_file.send(...)`.
4. Setup `dramatiq/worker-deployment.yaml` (k8s).
5. Admin UI: `dramatiq-dashboard` behind `/admin/jobs` with basic auth.

**Testing**
• Kill worker mid-processing → job picked up by other worker.
• Simulate failure 2× → third attempt succeeds.

**Roll-back**
Env `USE_SYNC_BACKGROUND=true` to revert to synchronous processing (dev-only).

**Docs / Ops**
Run-book “re-queue stuck jobs”, dashboard access instructions.

---


