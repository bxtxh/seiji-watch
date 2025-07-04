"""Models for policy issues and issue tags."""

from typing import Optional, List
from pydantic import Field

from .base import BaseRecord


class IssueTag(BaseRecord):
    """Issue tag model for categorizing policy issues."""
    
    name: str = Field(..., description="Tag name (e.g., カーボンニュートラル)")
    color_code: str = Field("#3B82F6", description="Hex color code for UI display")
    category: str = Field(..., description="Tag category (環境/経済/社会保障/外交/その他)")
    description: Optional[str] = Field(None, description="Optional tag description")
    
    def __repr__(self) -> str:
        return f"<IssueTag(name='{self.name}', category='{self.category}')>"


class Issue(BaseRecord):
    """Policy issue model."""
    
    title: str = Field(..., description="Issue title (max 100 chars)")
    description: str = Field(..., description="Detailed issue description")
    priority: str = Field("medium", description="Priority level (high/medium/low)")
    status: str = Field("active", description="Issue status (active/reviewed/archived)")
    
    # Relationships
    related_bills: Optional[List[str]] = Field(None, description="List of related Bill record IDs")
    issue_tags: Optional[List[str]] = Field(None, description="List of related IssueTag record IDs")
    
    # Metadata
    extraction_confidence: Optional[float] = Field(None, description="LLM extraction confidence score")
    review_notes: Optional[str] = Field(None, description="Admin review notes")
    is_llm_generated: bool = Field(False, description="Whether this issue was LLM-generated")
    
    def __repr__(self) -> str:
        return f"<Issue(title='{self.title[:30]}...', priority='{self.priority}')>"
    
    @property
    def tag_count(self) -> int:
        """Get the number of associated tags."""
        return len(self.issue_tags) if self.issue_tags else 0
    
    @property
    def bill_count(self) -> int:
        """Get the number of related bills."""
        return len(self.related_bills) if self.related_bills else 0