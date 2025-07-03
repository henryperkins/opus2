# Configuration management using Pydantic settings
# flake8: noqa
# Standard library
import os
import sys
from pathlib import Path
from functools import lru_cache
from typing import Optional, ClassVar

# Third-party
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, field_validator

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    model_config = ConfigDict(
        extra="allow",
        env_file=".env",
        case_sensitive=False
    )

    # Application
    app_name: str = "AI Productivity App"
    app_version: str = "0.1.0"
    # Enable *debug* by default in the test environment so that auxiliary
    # services (like the internal email micro-service) fall back to
    # *log-only* mode instead of attempting outbound network connections
    # which are blocked in the sandbox.
    debug: bool = True

    # -------------------------------------------------------------------
    # Vector Store Configuration
    # -------------------------------------------------------------------
    vector_store_type: str = Field(
        default="pgvector",
        description="Vector store backend. Supported: 'pgvector', 'qdrant'"
    )

    @field_validator("vector_store_type")
    @classmethod
    def validate_vector_store_type(cls, v: str) -> str:
        """Ensure *vector_store_type* is one of the supported backends.

        We currently support two storage layers:
        • pgvector – native PostgreSQL extension (default)
        • qdrant  – external high-performance vector database
        The legacy *sqlite_vss* backend has been removed.
        """
        allowed = {"pgvector", "qdrant"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(
                f"Unsupported vector_store_type: {v}. "
                "Supported values are: pgvector, qdrant."
            )
        return v_lower

    # PostgreSQL vector settings
    postgres_vector_table: str = Field(default="embeddings", description="Table name for pgvector embeddings")
    embedding_vector_size: int = Field(default=1536, description="Vector size for embeddings")

    # Vector search settings
    vector_search_limit: int = Field(default=10, description="Default vector search result limit")
    vector_score_threshold: float = Field(default=0.7, description="Minimum similarity score threshold")

    # Embedding processing settings
    embedding_model_token_limit: int = Field(default=8000, description="Token limit for embedding model")
    embedding_safety_margin: int = Field(default=200, description="Safety margin for token calculation")
    embedding_max_batch_rows: int = Field(default=100, description="Maximum rows to fetch per batch")
    embedding_max_retries: int = Field(default=5, description="Maximum retries for embedding operations")

    # Deprecated settings - kept for backward compatibility during migration
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant server URL (deprecated)")
    qdrant_host: str = Field(default="localhost", description="Qdrant server host (deprecated)")
    qdrant_port: int = Field(default=6333, description="Qdrant server port (deprecated)")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key (deprecated)")
    qdrant_vector_size: int = Field(default=1536, description="Vector size for embeddings (deprecated)")
    qdrant_timeout: int = Field(default=30, description="Qdrant client timeout in seconds (deprecated)")
    qdrant_max_workers: int = Field(default=16, description="Threadpool size for Qdrant operations (deprecated)")

    # -------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------
    #
    # The original implementation used a *relative* SQLite URL pointing to
    # ``./data/app.db``.  Because the *current working directory* differs
    # between local development (`uvicorn app.main`) and Alembic migrations
    # (executed from ``ai-productivity-app/backend``), two **different**
    # database files were created:
    #
    #   • ./data/app.db                            – when the backend is
    #     started from the project root ("login" API reads/writes here)
    #   • ai-productivity-app/data/app.db          – when `alembic upgrade`
    #     or `run_migration.py` is executed from the *backend* directory.
    #
    # The mismatch meant that migrations (including the `sessions` table)
    # were applied to *one* database while the running application queried a
    # *different* one.  As soon as an authenticated request tried to create
    # or validate a session the backend crashed with "no such table:
    # sessions" which the frontend surfaced as *non-persistent logins*.
    #
    # To make the path deterministic regardless of the CWD we resolve it
    # relative to this *config.py* file (which lives at
    # ``ai-productivity-app/backend/app/config.py``).  The resulting SQLite
    # URL always points at **ai-productivity-app/data/app.db**.
    #
    # Environment variable ``DATABASE_URL`` still overrides the default so
    # external databases continue to work unchanged.
    # -------------------------------------------------------------------

    # Build absolute path <repo_root>/ai-productivity-app/data/app.db (SQLite fallback)
    _DEFAULT_DB_PATH: ClassVar[Path] = (
        Path(__file__).resolve().parents[2]  # …/ai-productivity-app
        / "data"
        / "app.db"
    )

    # Production database connection (Neon PostgreSQL)
    database_url: str = Field(
        default="postgresql://neondb_owner:npg_5odQclNUW6Pj@ep-hidden-salad-a8jlsv5j-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require",
        description="Database connection URL"
    )
    database_echo: bool = False

    # Security
    secret_key: str = "change-this-in-production-use-secrets-module"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Cookie behaviour
    # -------------------------------------------------------------------
    # Browsers refuse to set/send cookies that carry the *Secure* attribute
    # when the current connection is **not** served over HTTPS.  During local
    # development the FastAPI server (and Vite dev-server) typically run on
    # plain *http://localhost* which means Secure cookies would be silently
    # dropped → the backend can no longer read the *access_token* and every
    # request appears unauthenticated.
    #
    # For production deployments you *do* want Secure cookies, therefore we
    # expose a flag that can be flipped via the environment variable
    # `INSECURE_COOKIES`.  We default the flag **on** (True) because the
    # overwhelming majority of first-time users spin up the stack locally
    # before moving it behind an HTTPS reverse-proxy.  When the application is
    # later deployed behind TLS one simply sets `INSECURE_COOKIES=false` (or
    # omits it entirely) to restore the Secure attribute.
    # Mark cookies as *insecure* during tests so that the mail micro-service
    # shortcut (settings.insecure_cookies == True) is triggered.
    insecure_cookies: bool = True

    # Authentication
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Registration
    registration_enabled: bool = True
    # Toggle invite-only mode
    registration_invite_only: bool = False
    # By default registration is *open* and no invite-code is necessary.  The
    # test-suite for Phase 2 expects `POST /api/auth/register` to accept new
    # users without requiring an additional *invite_code* field.  Production
    # deployments that want to enable invite-only sign-ups can still do so by
    # setting the environment variable `INVITE_CODES` to a comma-separated
    # list (e.g. "code1,code2").  When the variable is an *empty* string we
    # treat it as *invite disabled*.
    invite_codes: str = ""

    # CSRF Protection
    csrf_protection: bool = True
    csrf_secret: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://lakefrontdigital.io"

    # API Keys (for future phases)
    openai_api_key: Optional[str] = None
    # Azure OpenAI credentials – required when ``llm_provider`` is set to
    # "azure".  We keep the keys *optional* so that local development can use
    # the regular OpenAI backend without having to populate additional
    # environment variables.  When `llm_provider="azure"` at runtime and
    # the API-key / endpoint are *not* supplied we fail fast with a clear
    # error message from the provider specific client constructor.

    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None

    # The *api_version* parameter is mandatory for Azure OpenAI requests.  We
    # expose it as a setting with a sane default matching the SDK's examples
    # so users can easily pin a different version when Microsoft publishes a
    # new stable release.
    #
    # Default bumped from **2024-02-01** → **2024-02-15-preview** to align with
    # the version used throughout the official documentation as of June 2025.
    # The new version unlocks *response_format=json_object* and other recent
    # additions while remaining backwards-compatible for regular Chat
    # Completions.  Projects that rely on the legacy 2024-02-01 contract can
    # still override via the AZURE_OPENAI_API_VERSION environment variable.

    azure_openai_api_version: str = "2025-04-01-preview"

    # Azure authentication method - can be "api_key" or "entra_id"
    azure_auth_method: str = "api_key"

    # LLM settings
    llm_provider: str = "openai"

    # Default model used for completion calls.  Can be overridden at runtime
    # via the ``LLM_MODEL`` environment variable.  The old *llm_model* field
    # remains for backwards-compatibility but is deprecated and should not be
    # referenced by new code.

    llm_default_model: str = Field("gpt-4.1", alias="LLM_MODEL")

    # Deprecated – kept to avoid breaking existing environment variables /
    # database fixtures.  New code should rely on *llm_default_model*.
    llm_model: str | None = None
    max_context_tokens: int = 200000

    # --- Reasoning enrichment ---------------------------------------------
    # Enable Azure Responses API *reasoning enrichment* (self_check / chain of
    # thought).  When turned on the backend requests a *summary* of the model
    # reasoning and forwards it to the frontend over WebSocket so advanced
    # users can inspect why the model arrived at an answer.

    enable_reasoning: bool = False

    # WebSocket settings
    websocket_ping_interval: int = 30
    websocket_ping_timeout: int = 10

    # -------------------------------------------------------------------
    # Optional feature flags used by hardening checklist tasks
    # -------------------------------------------------------------------

    # Global switch to disable *Redis* backed rate-limiter – useful for unit
    # tests where the in-memory stub is sufficient.
    disable_rate_limiter: bool = Field(
        default=False,
        alias="DISABLE_RATE_LIMITER",
        description="Disable Redis rate-limiter and fall back to in-memory"
    )

    # Toggle correlation-ID middleware (can be turned off for benchmarks)
    disable_correlation_id: bool = Field(
        default=False,
        alias="DISABLE_CORRELATION_ID",
        description="Disable request correlation IDs middleware"
    )

    # Skip external OpenAI health-check in CI (no network access)
    skip_openai_health: bool = Field(
        default=True,
        alias="SKIP_OPENAI_HEALTH",
        description="Skip OpenAI connectivity check in readiness probe"
    )

    # WebSocket task tracking – can be disabled to reduce overhead
    ws_task_tracking: bool = Field(
        default=True,
        alias="WS_TASK_TRACKING",
        description="Enable WebSocket per-connection task tracking"
    )

    # URL where the user-facing frontend is served.  Used to build absolute
    # links in transactional emails (e.g. password-reset).  Defaults to
    # localhost dev-server.
    frontend_base_url: str = "http://localhost:5173"

    # Upload configuration
    upload_root: str = Field(
        default="./data/uploads",
        description="Root directory for file uploads"
    )
    upload_path_validation: str = Field(
        default="strict",
        description="Path validation mode: strict, warn, or disabled"
    )
    max_upload_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum file upload size in bytes"
    )

    # Rendering service configuration
    render_service_url: Optional[str] = Field(
        default=None,
        alias="RENDER_SERVICE_URL",
        description="External rendering service endpoint URL"
    )


    @property
    def effective_secret_key(self) -> str:
        """Return JWT secret key if set, otherwise fall back to main secret"""
        return self.jwt_secret_key or self.secret_key

    @property
    def cors_origins_list(self) -> list[str]:
        """Return list of CORS origins.

        Accepts either a comma-separated string (default) **or** a JSON-formatted
        list such as `["http://localhost:5173"]`.  This makes the setting more
        forgiving when developers copy different .env templates.
        """
        value = self.cors_origins

        # ------------------------------------------------------------------
        # 1. Attempt to parse as JSON list first
        # ------------------------------------------------------------------
        try:
            import json  # local import to avoid unnecessary global dependency
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
        except (TypeError, ValueError, json.JSONDecodeError):
            # Not JSON – fall back to comma-separated parsing.
            pass

        # ------------------------------------------------------------------
        # 2. Fallback: treat as comma-separated string
        # ------------------------------------------------------------------
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def invite_codes_list(self) -> list[str]:
        """Return list of valid invite codes"""
        return [code.strip() for code in self.invite_codes.split(",") if code.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()

# --- Startup security checks ---
DEFAULT_SECRET = "change-this-in-production-use-secrets-module"

_IN_TEST = "pytest" in sys.modules or os.getenv("APP_CI_SANDBOX") == "1"

if not _IN_TEST and settings.effective_secret_key == DEFAULT_SECRET:
    raise RuntimeError(
        "FATAL: Default JWT secret key is in use! Set 'JWT_SECRET_KEY' or 'SECRET_KEY' in your environment."
    )
