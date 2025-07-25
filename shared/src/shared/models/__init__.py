"""Data models for Diet Issue Tracker."""

from .base import BaseRecord, WeaviateEmbedding
from .bill import Bill, BillCategory, BillStatus
from .bills_issue_categories import BillsPolicyCategory
from .issue import Issue, IssueCategory, IssueTag
from .meeting import Meeting, Speech
from .member import Member, Party
from .vote import Vote, VoteResult

# Legacy aliases for backward compatibility
Base = BaseRecord
TimestampMixin = BaseRecord

__all__ = [
    "BaseRecord",
    "WeaviateEmbedding",
    "Bill",
    "BillStatus",
    "BillCategory",
    "Meeting",
    "Speech",
    "Member",
    "Party",
    "Vote",
    "VoteResult",
    "Issue",
    "IssueTag",
    "IssueCategory",
    "BillsPolicyCategory",
    # Legacy aliases
    "Base",
    "TimestampMixin",
]
