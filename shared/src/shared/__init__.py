"""
Shared data models and utilities for Diet Issue Tracker.

This package contains common data models, database schemas, and utility functions
that are shared across all services in the Diet Issue Tracker application.
"""

__version__ = "0.1.0"

# Import main components for easy access
from .database import (
    SessionLocal,
    create_engine,
    get_database_url,
    get_db,
    get_session,
)
from .models import (
    Base,
    Bill,
    BillCategory,
    BillStatus,
    Meeting,
    Member,
    Party,
    Speech,
    TimestampMixin,
    Vote,
    VoteResult,
)
from .types import (
    BillCreate,
    BillResponse,
    BillUpdate,
    MeetingCreate,
    MeetingResponse,
    MeetingUpdate,
    MemberCreate,
    MemberResponse,
    MemberUpdate,
    PartyCreate,
    PartyResponse,
    PartyUpdate,
    SpeechCreate,
    SpeechResponse,
    SpeechUpdate,
    VoteCreate,
    VoteResponse,
)
from .utils import (
    check_database_connection,
    create_tables,
    drop_tables,
    init_database,
    run_migrations,
)

__all__ = [
    # Models
    "Base",
    "TimestampMixin",
    "Bill",
    "BillStatus",
    "BillCategory",
    "Meeting",
    "Speech",
    "Member",
    "Party",
    "Vote",
    "VoteResult",
    # Schemas
    "BillCreate",
    "BillUpdate",
    "BillResponse",
    "MeetingCreate",
    "MeetingUpdate",
    "MeetingResponse",
    "SpeechCreate",
    "SpeechUpdate",
    "SpeechResponse",
    "MemberCreate",
    "MemberUpdate",
    "MemberResponse",
    "PartyCreate",
    "PartyUpdate",
    "PartyResponse",
    "VoteCreate",
    "VoteResponse",
    # Database
    "get_database_url",
    "create_engine",
    "get_session",
    "SessionLocal",
    "get_db",
    # Utils
    "init_database",
    "run_migrations",
    "create_tables",
    "drop_tables",
    "check_database_connection",
]
