"""Alembic migration environment — async engine pattern for SQLAlchemy 2.0 asyncpg."""
import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

from alembic import context

from app.config import settings
from app.database import Base

# ── Import all ORM models so their metadata is registered on Base ─────────────
# Models that already exist are imported directly.
# Models not yet created are wrapped in try/except so Alembic runs even before
# those files are present. Remove the try/except once each model is added.

# Existing models
try:
    from app.models import user  # noqa: F401
except ImportError:
    pass

# MedaZone models (added as they are implemented in subsequent tasks)
try:
    from app.models import field  # noqa: F401
except ImportError:
    pass

try:
    from app.models import slot  # noqa: F401
except ImportError:
    pass

try:
    from app.models import booking  # noqa: F401
except ImportError:
    pass

try:
    from app.models import subscription  # noqa: F401
except ImportError:
    pass

try:
    from app.models import slot_change_proposal  # noqa: F401
except ImportError:
    pass

try:
    from app.models import review  # noqa: F401
except ImportError:
    pass

try:
    from app.models import notification_preference  # noqa: F401
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────────────────────

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the shared declarative Base so all registered models are picked up
target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL only)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (async engine) ────────────────────────────────────────────────

def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine, hand a sync connection to Alembic, then dispose."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """Entry point for online mode — drives the async migration via asyncio.run()."""
    asyncio.run(run_async_migrations())


# ── Dispatch ──────────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
