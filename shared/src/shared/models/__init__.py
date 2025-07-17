"""Data models for Diet Issue Tracker."""

from .base import BaseRecord, WeaviateEmbedding
from .bill import Bill, BillStatus, BillCategory
from .meeting import Meeting, Speech
from .member import Member, Party
from .vote import Vote, VoteResult
from .issue import Issue, IssueTag, IssueCategory
from .bills_issue_categories import BillsPolicyCategory

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