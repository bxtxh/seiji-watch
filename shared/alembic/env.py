"""Alembic environment configuration for Diet Issue Tracker."""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add the src directory to the path so we can import our models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import all models to ensure they are registered with SQLAlchemy
from shared.models.base import Base
from shared.models.member import Party, Member
from shared.models.bill import Bill
from shared.models.meeting import Meeting, Speech
from shared.models.vote import Vote

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get database URL from environment or config."""
    # Try environment first (for different environments)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # Fallback to individual components
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "seiji_watch")
    db_user = os.getenv("DB_USER", "seiji_watch_user")
    db_password = os.getenv("DB_PASSWORD", "seiji_watch_pass")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get database URL
    database_url = get_database_url()
    
    # Override the sqlalchemy.url in the config
    config.set_main_option("sqlalchemy.url", database_url)
    
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            # Enable pgvector extension before running migrations
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()