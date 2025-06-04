from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.models.base import Base  # ← SQLAlchemy metadata
from app.models import user, project, session, timeline, code, embedding, chat  # ensure tables imported

# Alembic Config object
config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata   # ← critical line

def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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
