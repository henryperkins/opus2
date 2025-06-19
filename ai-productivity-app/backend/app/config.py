# Configuration management using Pydantic settings
# flake8: noqa
# Standard library
from pathlib import Path
from functools import lru_cache
from typing import Optional, ClassVar

# Third-party
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field

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
    debug: bool = False

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

    # Build absolute path <repo_root>/ai-productivity-app/data/app.db
    _DEFAULT_DB_PATH: ClassVar[Path] = (
        Path(__file__).resolve().parents[2]  # …/ai-productivity-app
        / "data"
        / "app.db"
    )

    database_url: str = f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}"
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
    insecure_cookies: bool = True

    # Authentication
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Registration
    registration_enabled: bool = True
    invite_codes: str = "code1,code2,code3"

    # CORS
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

    # The *api_version* parameter is mandatory for Azure OpenAI requests.  We
    # expose it as a setting with a sane default matching the SDK's examples
    # so users can easily pin a different version when Microsoft publishes a
    # new stable release. Use "preview" to enable Azure Responses API.

    azure_openai_api_version: str = "2024-02-01"

    # Azure authentication method - can be "api_key" or "entra_id"
    azure_auth_method: str = "api_key"

    # LLM settings
    llm_provider: str = "openai"

    # Default model used for completion calls.  Can be overridden at runtime
    # via the ``LLM_MODEL`` environment variable.  The old *llm_model* field
    # remains for backwards-compatibility but is deprecated and should not be
    # referenced by new code.

    llm_default_model: str = Field("gpt-3.5-turbo", alias="LLM_MODEL")

    # Deprecated – kept to avoid breaking existing environment variables /
    # database fixtures.  New code should rely on *llm_default_model*.
    llm_model: str | None = None
    max_context_tokens: int = 8000

    # WebSocket settings
    websocket_ping_interval: int = 30
    websocket_ping_timeout: int = 10

    # URL where the user-facing frontend is served.  Used to build absolute
    # links in transactional emails (e.g. password-reset).  Defaults to
    # localhost dev-server.
    frontend_base_url: str = "http://localhost:5173"


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
