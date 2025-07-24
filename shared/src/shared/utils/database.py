"""Database utility functions."""

import logging
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..database.base import create_engine
from ..models.base import Base

logger = logging.getLogger(__name__)


def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        engine = create_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {e}")
        return False


def create_tables() -> None:
    """Create all database tables."""
    try:
        engine = create_engine()

        # Enable pgvector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except SQLAlchemyError as e:
        logger.error(f"Failed to create tables: {e}")
        raise


def drop_tables() -> None:
    """Drop all database tables."""
    try:
        engine = create_engine()
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")

    except SQLAlchemyError as e:
        logger.error(f"Failed to drop tables: {e}")
        raise


def run_migrations(revision: str = "head") -> None:
    """Run Alembic migrations."""
    try:
        # Get the path to the shared package directory
        shared_dir = Path(__file__).parent.parent.parent.parent

        # Run alembic upgrade command
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=shared_dir,
            capture_output=True,
            text=True,
            check=True
        )

        logger.info(f"Migrations completed successfully: {result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        raise


def init_database() -> None:
    """Initialize database with tables and initial data."""
    logger.info("Initializing database...")

    # Check connection first
    if not check_database_connection():
        raise RuntimeError("Cannot connect to database")

    try:
        # Run migrations to create tables
        run_migrations()
        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_migration_status() -> dict:
    """Get current migration status."""
    try:
        shared_dir = Path(__file__).parent.parent.parent.parent

        # Get current revision
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=shared_dir,
            capture_output=True,
            text=True,
            check=True
        )

        current_revision = result.stdout.strip()

        # Get head revision
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "heads"],
            cwd=shared_dir,
            capture_output=True,
            text=True,
            check=True
        )

        head_revision = result.stdout.strip()

        return {
            "current": current_revision,
            "head": head_revision,
            "up_to_date": current_revision == head_revision
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get migration status: {e.stderr}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error getting migration status: {e}")
        return {"error": str(e)}
