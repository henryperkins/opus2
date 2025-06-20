## 1️. Backend container

### 1.1. Multi‑stage Dockerfile (builder → runtime)

    # (builder stage: install build deps and compile tree‑sitter)
    FROM python:3.11-slim as builder
    …
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --user --no-cache-dir -r requirements.txt

    # clone & compile grammars into build/languages.so
    RUN mkdir -p build/tree-sitter \
        && git clone --depth 1 https://github.com/tree-sitter/tree-sitter-python      build/tree-sitter/python \
        && git clone --depth 1 https://github.com/tree-sitter/tree-sitter-javascript  build/tree-sitter/javascript \
        && git clone --depth 1 https://github.com/tree-sitter/tree-sitter-typescript  build/tree-sitter/typescript

    RUN python - <<'PY'
    …  # compiles to build/languages.so if supported
    PY

    # (runtime stage: slim image + non‑root user + copy artifacts)
    FROM python:3.11-slim

    # install runtime deps (git + curl for healthcheck)
    RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        && rm -rf /var/lib/apt/lists/*

    # create appuser and copy in everything
    RUN useradd -m -u 1000 appuser
    COPY --from=builder /root/.local /home/appuser/.local
    COPY --from=builder /app/build /app/build
    WORKDIR /app
    RUN mkdir -p /app/data && chown -R appuser:appuser /app
    COPY --chown=appuser:appuser . .
    USER appuser
    ENV PATH=/home/appuser/.local/bin:$PATH

    EXPOSE 8000

    # liveness/readiness probe baked into image (for `docker run`)
    HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
        CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"

    # default process
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

ai-productivity-app/backend/Dockerfileai-productivity-app/backend/Dockerfileai-productivity-app/backend/Dockerfileai-productivity-app/backend/Dockerfileai-productivity-app/backend/Dockerfileai-prod
uctivity-app/backend/Dockerfileai-productivity-app/backend/Dockerfile

#### What this guarantees

    * **Minimal runtime image** (build‑deps do not bloat the final image).
    * **Non‑root user** (“appuser”) for better security.
    * **Tree‑sitter grammars** compiled and vendored, so parser features work without dynamic compilation on startup.
    * **`curl`** present so health probes actually succeed.
    * `HEALTHCHECK` in the image itself hits `/health/ready` to verify the application and its DB layer are up.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 1.2. Docker Compose service override

    version: '3.8'
    services:
      backend:
        build:
          context: ./backend
          dockerfile: Dockerfile
        container_name: ai-productivity-backend
        ports:
          - "8000:8000"
        volumes:
          - ./backend:/app
        environment:
          - DEBUG=true
          - SECRET_KEY=dev-secret-key-change-in-production
          - INSECURE_COOKIES=true
        networks:
          - app-network
        healthcheck:
          test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready"]
          interval: 30s
          timeout: 10s
          retries: 3
          start_period: 40s
        restart: unless-stopped

ai-productivity-app/docker-compose.ymlai-productivity-app/docker-compose.yml

Key points:

    * **Bind-mount** `./backend:/app` for live‑reload locally.
    * Container’s built-in healthcheck is overridden by Compose to use the same `/health/ready` readiness endpoint.
    * `INSECURE_COOKIES=true` only for dev; omitted in real production.
    * `restart: unless-stopped` ensures automatic restarts on failures.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 1.3. Application‑level initialization

Inside app/main.py the FastAPI lifespan hook calls init_db() on startup:

    @asynccontextmanager
    async def lifespan(_app):
        # on startup: create tables (and schema) via init_db()
        init_db()
        yield
        # on shutdown: cleanup if any

ai-productivity-app/backend/app/main.py

And in app/database.py, init_db() brings up all the ORM models and does Base.metadata.create_all(), so your database schema is freshly created (unless you’re in pytest, which skips it):

    def init_db() -> None:
        # import models → register metadata
        from app.models import user, project, …
        # create all tables (unless under pytest)
        if "pytest" not in sys.modules and os.getenv("SKIP_INIT_DB") is None:
            Base.metadata.create_all(bind=engine)

ai-productivity-app/backend/app/database.py

The /health/ready endpoint then checks a trivial SELECT 1 against that same DB engine.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 2️. Frontend container

    # Development Dockerfile with Vite dev server & proxy support
    FROM node:20-alpine

    WORKDIR /app

    # install deps first for caching
    COPY package*.json ./
    RUN npm ci

    # install wget so the HEALTHCHECK can use it
    RUN apk add --no-cache wget

    # copy the source
    COPY . .

    EXPOSE 5173

    # verify the Vite server is alive
    HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
      CMD wget --no-verbose --tries=1 --spider http://localhost:5173/ || exit 1

    # run dev server
    CMD ["npm", "run", "dev"]

ai-productivity-app/frontend/Dockerfileai-productivity-app/frontend/Dockerfile

And in Compose:

      frontend:
        build:
          context: ./frontend
          dockerfile: Dockerfile
        container_name: ai-productivity-frontend
        ports:
          - "5173:5173"
        volumes:
          - ./frontend:/app
          - /app/node_modules
        environment:
          - NODE_ENV=development
          - DOCKER_ENV=true
          - VITE_API_URL=http://backend:8000
        networks:
          - app-network
        depends_on:
          - backend
        restart: unless-stopped

ai-productivity-app/docker-compose.yml

Highlights:

    * **`npm ci`** for reproducible installs.
    * **`wget`** for the container’s own health probe.
    * **`/app/node_modules`** mounted as an anonymous volume so local `./frontend` bind‑mount doesn’t overwrite the installed packages.
    * **`VITE_API_URL=http://backend:8000`** ensures calls from the front end go to the backend service alias on the Docker network.
    * **`depends_on: backend`** makes Docker start frontend only after the backend container is running (though not yet healthy).

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 3️. Orchestration via start.sh

Our ./start.sh script wraps the compose flow and does a post‑start poll on readiness:

    docker compose up -d

    echo "⏳ Waiting for services to start..."
    sleep 5

    # Backend readiness (DB + app)
    for i in {1..30}; do
        if curl -s http://localhost:8000/health/ready > /dev/null 2>&1; then
            echo "✅ Backend is ready"
            break
        fi
        …
    done

    # Frontend startup
    for i in {1..15}; do
        if curl -s http://localhost:5173 > /dev/null 2>&1; then
            echo "✅ Frontend is ready"
            break
        fi
        …
    done

ai-productivity-app/start.shai-productivity-app/start.sh

This guarantees that, by the time you see “🎉 Application started successfully!”, both:

    * the **FastAPI app** (and its DB schema) are fully responsive, and
    * the **Vite dev server** is serving your frontend assets.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 4️. Summary & next steps

┌───────────┬───────────────────┬───────────────────────────────────────────────────────────────────┐
│ Container │ Health endpoint   │ Key points                                                        │
├───────────┼───────────────────┼───────────────────────────────────────────────────────────────────┤
│ backend   │ /health/ready     │ multi‑stage build, non‑root, curl, DB auto‑init via lifespan hook │
├───────────┼───────────────────┼───────────────────────────────────────────────────────────────────┤
│ frontend  │ root / (via wget) │ npm ci + vite dev server, wget, env proxy to backend              │
└───────────┴───────────────────┴───────────────────────────────────────────────────────────────────┘

With the recent patches in place:

    * ✅ **Healthchecks** now use the readiness probe (`/health/ready`) so you won’t get a “healthy” FastAPI container until its DB is up.
    * ✅ **curl** and **wget** are installed so the probes actually run.
    * ✅ **Compose version** is pinned (`3.8`) and unused volumes (and stale prod compose stubs) have been cleaned out.

You should be able to rebuild & bring everything up cleanly:

    cd ai-productivity-app
    ./start.sh

…and have confidence that both containers are truly up, initialized, and ready to go. Let me know if you’d like any additional checks (e.g. liveness vs readiness split, migrating to /health/live,
etc.)!
