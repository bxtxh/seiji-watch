"""Models for Diet bills and legislation."""

import enum
from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import Field

from .base import BaseRecord


class BillStatus(enum.Enum):
    """Status of a bill in the legislative process."""
    
    BACKLOG = "backlog"           # 待機中
    UNDER_REVIEW = "under_review" # 審議中
    PENDING_VOTE = "pending_vote" # 採決待ち
    PASSED = "passed"             # 成立
    REJECTED = "rejected"         # 否決
    WITHDRAWN = "withdrawn"       # 撤回
    EXPIRED = "expired"           # 廃案


class BillCategory(enum.Enum):
    """Categories for bill classification."""
    
    BUDGET = "budget"                    # 予算・決算
    TAXATION = "taxation"                # 税制
    SOCIAL_SECURITY = "social_security"  # 社会保障
    FOREIGN_AFFAIRS = "foreign_affairs"  # 外交・国際
    ECONOMY = "economy"                  # 経済・産業
    EDUCATION = "education"              # 教育・文化
    ENVIRONMENT = "environment"          # 環境・エネルギー
    INFRASTRUCTURE = "infrastructure"    # インフラ・交通
    DEFENSE = "defense"                  # 防衛・安全保障
    JUDICIARY = "judiciary"              # 司法・法務
    ADMINISTRATION = "administration"    # 行政・公務員
    OTHER = "other"                      # その他


class Bill(BaseRecord):
    """Diet bill model."""
    
    # Basic identification
    bill_number: str = Field(..., description="Official bill number")
    title: str = Field(..., description="Bill title")
    title_en: Optional[str] = Field(None, description="English title")
    short_title: Optional[str] = Field(None, description="Short title/abbreviation")
    
    # Content
    summary: Optional[str] = Field(None, description="Bill summary")
    full_text: Optional[str] = Field(None, description="Full bill text")
    purpose: Optional[str] = Field(None, description="Purpose of the bill")
    
    # Classification
    status: BillStatus = Field(BillStatus.BACKLOG, description="Current bill status")
    category: Optional[BillCategory] = Field(None, description="Bill category")
    bill_type: Optional[str] = Field(None, description="Bill type (government/member)")
    
    # Timeline
    submitted_date: Optional[str] = Field(None, description="Submission date (YYYY-MM-DD)")
    first_reading_date: Optional[str] = Field(None, description="First reading date")
    committee_referral_date: Optional[str] = Field(None, description="Committee referral date")
    committee_report_date: Optional[str] = Field(None, description="Committee report date")
    final_vote_date: Optional[str] = Field(None, description="Final vote date")
    promulgated_date: Optional[str] = Field(None, description="Promulgation date")
    
    # Session information
    diet_session: Optional[str] = Field(None, description="Diet session number")
    house_of_origin: Optional[str] = Field(None, description="House of origin")
    
    # Submitter information
    submitter_type: Optional[str] = Field(None, description="Submitter type")
    submitting_members: Optional[List[str]] = Field(None, description="List of submitting member IDs")
    sponsoring_ministry: Optional[str] = Field(None, description="Sponsoring ministry")
    
    # URLs and references
    diet_url: Optional[str] = Field(None, description="Diet website URL")
    pdf_url: Optional[str] = Field(None, description="PDF document URL")
    related_bills: Optional[List[str]] = Field(None, description="List of related bill IDs")
    
    # LLM-generated content
    ai_summary: Optional[str] = Field(None, description="AI-generated summary")
    key_points: Optional[List[str]] = Field(None, description="List of key points")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    impact_assessment: Optional[Dict[str, Any]] = Field(None, description="AI impact analysis")
    
    # Metadata
    is_controversial: bool = Field(False, description="Whether the bill is controversial")
    priority_level: str = Field("normal", description="Priority level (high/normal/low)")
    estimated_cost: Optional[str] = Field(None, description="Estimated cost")
    
    # Issue Management
    related_issues: Optional[List[str]] = Field(None, description="List of related Issue record IDs")
    issue_tags: Optional[List[str]] = Field(None, description="List of related IssueTag record IDs")
    
    def __repr__(self) -> str:
        return f"<Bill(number='{self.bill_number}', title='{self.title[:50]}...', status='{self.status.value}')>"
    
    @property
    def is_passed(self) -> bool:
        """Check if the bill has been passed."""
        return self.status == BillStatus.PASSED
    
    @property
    def is_pending(self) -> bool:
        """Check if the bill is still in progress."""
        return self.status in [BillStatus.BACKLOG, BillStatus.UNDER_REVIEW, BillStatus.PENDING_VOTE]
    
    @property
    def days_since_submission(self) -> Optional[int]:
        """Calculate days since bill submission."""
        if not self.submitted_date:
            return None
        try:
            from datetime import datetime
            submitted = datetime.strptime(self.submitted_date, "%Y-%m-%d").date()
            return (date.today() - submitted).days
        except ValueError:
            return None