"""Base models and mixins for all database models."""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr


class Base:
    """Base class for all database models."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()
    
    id = Column(Integer, primary_key=True, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


# Create the declarative base
Base = declarative_base(cls=Base)


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )