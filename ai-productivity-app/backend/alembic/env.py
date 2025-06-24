from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

# --- SQLAlchemy metadata ---------------------------------------------------
from app.models.base import Base  # type: ignore  # noqa: F401 – imported for side-effects

# Import all model modules so their tables are registered on *Base.metadata*.
# Heavy optional dependencies (e.g. *numpy* required by the *embedding* models)
# are not available inside the lightweight CI sandbox.  We therefore import
# core modules unconditionally and load the *embedding* package lazily inside
# a try/except block so migrations continue to run even when these extras are
# missing.

from importlib import import_module

# Core tables that never pull heavy third-party libraries.
for _mod in ("user", "project", "session", "timeline", "code", "chat"):
    import_module(f"app.models.{_mod}")  # noqa: WPS421 – import for side-effects

# Optional embedding models – safe to ignore when dependencies are absent.
try:
    import_module("app.models.embedding")  # noqa: WPS421 – import for side-effects
except ModuleNotFoundError:  # pragma: no cover – optional dependency missing
    pass

# Alembic Config object
config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata   # ← critical line

def run_migrations_offline():
    # Use DATABASE_URL environment variable if available, otherwise use config
    database_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # Use DATABASE_URL environment variable if available, otherwise use config
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Override the URL in the config section
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = database_url
    else:
        configuration = config.get_section(config.config_ini_section)
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
