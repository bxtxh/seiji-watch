"""Database session management for FastAPI applications."""

from typing import Generator
from sqlalchemy.orm import Session

from .base import create_engine, get_session


# Create global engine and session factory
engine = create_engine()
SessionLocal = get_session(engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    
    Usage in FastAPI route:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()