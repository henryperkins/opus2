# Configuration management using Pydantic settings
# flake8: noqa
# Standard library
import os
import sys

# Detect test environment early so helpers can reference it
_IN_TEST = "pytest" in sys.modules or os.getenv("APP_CI_SANDBOX") == "1"
from pathlib import Path
from functools import lru_cache
from typing import Optional, ClassVar

# Third-party
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, field_validator


class Settings(BaseSettings):
    """Application settings."""
    app_name: str = "AI Productivity App"
    app_version: str = "0.1.0"
    debug: bool = False
    debug_sql: bool = False

    # -------------------------------------------------------------------
    # Vector Store Configuration
    # -------------------------------------------------------------------
    vector_store_type: str = Field(
        default="pgvector",
        description="Vector store backend. Supported: 'pgvector', 'qdrant'",
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

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Ensure *llm_provider* is one of the supported providers."""
        allowed = {"openai", "azure", "anthropic"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(
                f"Unsupported llm_provider: {v}. "
                "Supported values are: openai, azure, anthropic."
            )
        return v_lower

    @field_validator("claude_thinking_mode")
    @classmethod
    def validate_claude_thinking_mode(cls, v: str) -> str:
        """Ensure *claude_thinking_mode* is one of the supported modes."""
        allowed = {"off", "enabled", "aggressive"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(
                f"Unsupported claude_thinking_mode: {v}. "
                "Supported values are: off, enabled, aggressive."
            )
        return v_lower

    @field_validator("reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, v: str) -> str:
        """Ensure *reasoning_effort* is one of the supported levels."""
        allowed = {"low", "medium", "high"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(
                f"Unsupported reasoning_effort: {v}. "
                "Supported values are: low, medium, high."
            )
        return v_lower

    # PostgreSQL vector settings
    postgres_vector_table: str = Field(
        default="embeddings", description="Table name for pgvector embeddings"
    )
    embedding_vector_size: int = Field(
        default=1536, description="Vector size for embeddings"
    )

    # Vector search settings
    vector_search_limit: int = Field(
        default=10, description="Default vector search result limit"
    )
    vector_score_threshold: float = Field(
        default=0.7, description="Minimum similarity score threshold"
    )

    # Embedding processing settings
    embedding_model_token_limit: int = Field(
        default=8000, description="Token limit for embedding model"
    )
    embedding_safety_margin: int = Field(
        default=200, description="Safety margin for token calculation"
    )
    embedding_max_batch_rows: int = Field(
        default=100, description="Maximum rows to fetch per batch"
    )
    embedding_max_retries: int = Field(
        default=5, description="Maximum retries for embedding operations"
    )
    embedding_max_concurrency: int = Field(
        default=1, description="Maximum concurrent embedding requests"
    )

    # -------------------------------------------------------------------
    # Qdrant Specific Configuration
    # -------------------------------------------------------------------
    # The application supports both *pgvector* and *qdrant* back-ends as
    # selected by *vector_store_type*.  When ``vector_store_type == "qdrant"``
    # the :pyfile:`app.services.qdrant_service` accesses the following
    # settings.  They were previously removed which caused an
    # ``AttributeError`` on startup.  We restore them here with sensible
    # defaults suitable for local development while allowing full override
    # through environment variables.
    #
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Base URL of the Qdrant server",
    )
    qdrant_api_key: Optional[str] = Field(
        default=None,
        description="API key for Qdrant Cloud or protected instances",
    )
    qdrant_timeout: int = Field(
        default=30,
        description="Request timeout (seconds) for Qdrant client operations",
    )
    qdrant_vector_size: int = Field(
        default=1536,
        description="Vector size for embeddings stored in Qdrant",
    )
    qdrant_max_workers: int = Field(
        default=16,
        description="Maximum worker threads in the Qdrant thread-pool executor",
    )

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
        Path(__file__).resolve().parents[2] / "data" / "app.db"  # …/ai-productivity-app
    )

    # Database connection - must be set via environment variable for production
    database_url: str = Field(
        default=None,
        description="Database connection URL - required via DATABASE_URL environment variable",
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

    # CORS - default to localhost for development
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

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

    # Anthropic API credentials – required when ``llm_provider`` is set to
    # "anthropic".  Similar to Azure OpenAI, we keep this optional for
    # local development flexibility.
    anthropic_api_key: Optional[str] = None

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

    #
    # The classic *data-plane* API versions (for example **2025-04-01-preview**)
    # are superseded by the unified *v1 preview* surface introduced mid-2025.
    # The new surface requires ``api-version=preview`` on every request and is
    # the only one that supports the **Responses API**.  We therefore switch
    # the default to the simple literal "preview" so that helpers which still
    # rely on this setting (e.g. legacy health-check routes) stay functional
    # without manual overrides.
    azure_openai_api_version: str = "preview"

    # Azure authentication method - can be "api_key" or "entra_id"
    azure_auth_method: str = "api_key"

    # -------------------------------------------------------------------
    # Validators ---------------------------------------------------------
    # -------------------------------------------------------------------

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is properly configured."""
        if not v:
            # In test environments, provide a safe default
            if _IN_TEST:
                return f"sqlite:///{cls._DEFAULT_DB_PATH}"
            raise ValueError(
                "DATABASE_URL environment variable is required for production. "
                "Please set it to your PostgreSQL connection string."
            )

        # Warn about hardcoded production values
        if "neon.tech" in v or "amazonaws.com" in v:
            if not os.getenv("DATABASE_URL"):
                raise ValueError(
                    "Production database URL detected but DATABASE_URL environment variable not set. "
                    "For security, production database connections must be configured via environment variables."
                )

        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Ensure CORS origins are properly configured for production."""
        if not _IN_TEST:
            # Check if production domains are hardcoded
            production_patterns = ['.io', '.com', '.net', '.org', 'https://']
            has_production_domain = any(pattern in v for pattern in production_patterns if pattern != 'localhost')

            if has_production_domain and not os.getenv("CORS_ORIGINS"):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Production CORS origins detected in code. "
                    "Consider setting CORS_ORIGINS environment variable instead."
                )

        return v

    @field_validator("azure_auth_method")
    @classmethod
    def validate_azure_auth_method(cls, v: str) -> str:
        """Ensure *azure_auth_method* is either ``api_key`` or ``entra_id``.

        The setting is referenced by :pyfile:`app.llm.providers.azure_provider`
        to decide which authentication strategy to configure for
        *AsyncAzureOpenAI*.  Any other value would lead to a silent fallback
        to the default branch, therefore we fail early during application
        start-up.
        """
        allowed = {"api_key", "entra_id"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(
                f"Unsupported azure_auth_method: {v}. "
                "Supported values are: api_key, entra_id."
            )
        return v_lower

    # LLM settings
    llm_provider: str = "openai"

    # Default model used for completion calls.  Can be overridden at runtime
    # via the ``LLM_MODEL`` environment variable.  The old *llm_model* field
    # remains for backwards-compatibility but is deprecated and should not be
    # referenced by new code.
    #
    # Updated to use gpt-4o which is available in Azure Responses API

    llm_default_model: str = Field("gpt-4o-mini", alias="LLM_MODEL")
    max_context_tokens: int = 200000

    # --- Reasoning enrichment (Azure OpenAI / OpenAI only) ---------------
    # Enable Azure Responses API *reasoning enrichment* for supported models.
    # Per o3/o4-mini documentation: reasoning models produce internal chain of thought
    # automatically - don't try to induce additional reasoning.
    # This setting applies to non-reasoning models when using Responses API.
    # Only applies when llm_provider is "azure" or "openai"

    enable_reasoning: bool = False

    # Reasoning effort levels for Azure/OpenAI models: "low", "medium", "high"
    reasoning_effort: str = Field(
        default="medium",
        description="Reasoning effort level for Azure/OpenAI models"
    )

    # --- Extended Thinking Configuration (Anthropic Claude only) ----------
    # Claude extended thinking settings for transparent reasoning
    # Only applies when llm_provider is "anthropic"

    # Enable extended thinking for Claude models (Opus 4, Sonnet 4, Sonnet 3.7)
    claude_extended_thinking: bool = True

    # Default thinking token budget (minimum 1024, recommended 16k+ for complex tasks)
    claude_thinking_budget_tokens: int = 16384

    # Thinking modes: "off", "enabled", "aggressive"
    claude_thinking_mode: str = Field(
        default="enabled",
        description="Extended thinking mode for Claude models only"
    )

    # Enable thinking transparency in responses for Claude
    claude_show_thinking_process: bool = True

    # Auto-adjust thinking budget based on task complexity
    claude_adaptive_thinking_budget: bool = True

    # Maximum thinking budget for complex tasks
    claude_max_thinking_budget: int = 65536

    # Comma-separated list of Claude models that support the "thinking" feature
    claude_thinking_models: str = Field(
        default="claude-opus-4-20250514,claude-sonnet-4-20250514,claude-3-5-sonnet-20241022,claude-3-5-sonnet-latest",
        description="Comma-separated list of Claude models that support the 'thinking' feature"
    )

    # Tool calling optimization settings (based on o3/o4-mini guidance)
    max_tools_per_request: int = Field(
        default=10,
        description="Maximum number of tools to include per request (ideally <100 for best performance)",
    )
    tool_timeout: int = Field(
        default=30, description="Timeout for individual tool execution in seconds"
    )

    # LLM retry configuration
    llm_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for LLM calls"
    )
    llm_retry_max_wait: int = Field(
        default=60,
        description="Maximum wait time between retries in seconds"
    )
    llm_timeout_seconds: int = Field(
        default=300,
        description="Timeout for LLM API calls in seconds"
    )

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
        description="Disable Redis rate-limiter and fall back to in-memory",
    )

    # Toggle correlation-ID middleware (can be turned off for benchmarks)
    disable_correlation_id: bool = Field(
        default=False,
        alias="DISABLE_CORRELATION_ID",
        description="Disable request correlation IDs middleware",
    )

    # Skip external OpenAI health-check in CI (no network access)
    skip_openai_health: bool = Field(
        default=True,
        alias="SKIP_OPENAI_HEALTH",
        description="Skip OpenAI connectivity check in readiness probe",
    )

    # WebSocket task tracking – can be disabled to reduce overhead
    ws_task_tracking: bool = Field(
        default=True,
        alias="WS_TASK_TRACKING",
        description="Enable WebSocket per-connection task tracking",
    )


    # URL where the user-facing frontend is served.  Used to build absolute
    # links in transactional emails (e.g. password-reset).  Defaults to
    # localhost dev-server.
    frontend_base_url: str = "http://localhost:5173"

    # Upload configuration
    upload_root: str = Field(
        default="./data/uploads", description="Root directory for file uploads"
    )
    upload_path_validation: str = Field(
        default="strict", description="Path validation mode: strict, warn, or disabled"
    )
    max_upload_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum file upload size in bytes",
    )

    # Rendering service configuration
    render_service_url: Optional[str] = Field(
        default=None,
        alias="RENDER_SERVICE_URL",
        description="External rendering service endpoint URL",
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

# Additional production safety checks
if not _IN_TEST:
    # Check for required environment variables in production
    required_for_production = []

    if not os.getenv("DATABASE_URL"):
        required_for_production.append("DATABASE_URL")

    if not os.getenv("JWT_SECRET_KEY") and not os.getenv("SECRET_KEY"):
        required_for_production.append("JWT_SECRET_KEY or SECRET_KEY")

    if required_for_production:
        raise RuntimeError(
            f"FATAL: Missing required environment variables for production: {', '.join(required_for_production)}"
        )
