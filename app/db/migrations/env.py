# app/db/migrations/env.py
"""
Alembic migration environment configuration.

Handles both sync and async database connections for migrations.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.config import get_settings
from app.db.base import Base
from app.db.config import get_database_config

# Import all models to ensure they're registered
try:
    from app.db.models import *  # noqa: F401, F403
except ImportError:
    # Models may not exist yet during initial setup
    pass

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate
target_metadata = Base.metadata

# Database URL from configuration
settings = get_settings()
db_config = get_database_config()
database_url = db_config.get_database_url(async_driver=False)  # Use sync driver for migrations

# Set the URL in alembic config
config.set_main_option('sqlalchemy.url', database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Execute migrations with the provided connection.

    Args:
        connection: Database connection
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using synchronous engine.

    We use a synchronous engine for migrations to avoid the async driver issue.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration['sqlalchemy.url'] = database_url

    # Use standard create_engine for migrations (not async)
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


# Determine migration mode and run
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
