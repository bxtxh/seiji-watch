"""Database configuration and utilities."""

import os

from sqlalchemy import Engine
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """Get database URL from environment variables."""

    # Try DATABASE_URL first (for Cloud Run and production)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # Fallback to individual components (for local development)
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "seiji_watch")
    db_user = os.getenv("DB_USER", "seiji_watch_user")
    db_password = os.getenv("DB_PASSWORD", "seiji_watch_pass")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def create_engine(database_url: str | None = None, **kwargs) -> Engine:
    """Create SQLAlchemy engine with optimized settings."""

    if database_url is None:
        database_url = get_database_url()

    # Default engine settings optimized for our use case
    default_kwargs = {
        "pool_size": 20,
        "max_overflow": 0,
        "pool_pre_ping": True,
        "pool_recycle": 300,  # 5 minutes
        "echo": os.getenv("DEBUG", "false").lower() == "true",
    }

    # Merge with provided kwargs
    engine_kwargs = {**default_kwargs, **kwargs}

    return sa_create_engine(database_url, **engine_kwargs)


def get_session(engine: Engine) -> sessionmaker[Session]:
    """Create session factory for the given engine."""

    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
