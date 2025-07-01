"""Models for Diet bills and legislation."""

import enum
from sqlalchemy import Column, String, Text, Boolean, Enum, Date, Index, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .base import Base, TimestampMixin


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


class Bill(Base, TimestampMixin):
    """Diet bill model."""
    
    __tablename__ = "bills"
    
    # Basic identification
    bill_number = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    title_en = Column(String(1000), nullable=True)  # English title
    short_title = Column(String(200), nullable=True)  # 略称
    
    # Content
    summary = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)
    purpose = Column(Text, nullable=True)  # 法案の目的
    
    # Classification
    status = Column(Enum(BillStatus), default=BillStatus.BACKLOG, nullable=False, index=True)
    category = Column(Enum(BillCategory), nullable=True, index=True)
    bill_type = Column(String(50), nullable=True, index=True)  # 政府提出/議員提出など
    
    # Timeline
    submitted_date = Column(Date, nullable=True, index=True)
    first_reading_date = Column(Date, nullable=True)
    committee_referral_date = Column(Date, nullable=True)
    committee_report_date = Column(Date, nullable=True)
    final_vote_date = Column(Date, nullable=True)
    promulgated_date = Column(Date, nullable=True)
    
    # Session information
    diet_session = Column(String(20), nullable=True, index=True)  # 国会回次
    house_of_origin = Column(String(20), nullable=True)  # 提出院（衆議院/参議院）
    
    # Submitter information
    submitter_type = Column(String(20), nullable=True)  # government/member
    submitting_members = Column(JSON, nullable=True)  # List of member IDs for member bills
    sponsoring_ministry = Column(String(100), nullable=True)  # 主管省庁
    
    # URLs and references
    diet_url = Column(String(500), nullable=True)
    pdf_url = Column(String(500), nullable=True)
    related_bills = Column(JSON, nullable=True)  # List of related bill IDs
    
    # LLM-generated content
    ai_summary = Column(Text, nullable=True)  # AI-generated summary
    key_points = Column(JSON, nullable=True)  # List of key points
    tags = Column(JSON, nullable=True)  # List of tags
    impact_assessment = Column(JSON, nullable=True)  # AI impact analysis
    
    # Vector embeddings for semantic search
    title_embedding = Column(Vector(1536), nullable=True)  # OpenAI embedding dimension
    content_embedding = Column(Vector(1536), nullable=True)
    
    # Metadata
    is_controversial = Column(Boolean, default=False, nullable=False)
    priority_level = Column(String(20), default="normal", nullable=False)  # high/normal/low
    estimated_cost = Column(String(100), nullable=True)  # 予算規模
    
    # Relationships
    speeches = relationship("Speech", back_populates="related_bill", lazy="dynamic")
    votes = relationship("Vote", back_populates="bill", lazy="dynamic")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_bill_status_date", "status", "submitted_date"),
        Index("idx_bill_category_session", "category", "diet_session"),
        Index("idx_bill_timeline", "submitted_date", "final_vote_date"),
        Index("idx_bill_search", "title", "bill_number"),
        Index("idx_bill_content_embedding", "content_embedding"),
        Index("idx_bill_title_embedding", "title_embedding"),
    )
    
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
    def days_since_submission(self) -> int | None:
        """Calculate days since bill submission."""
        if not self.submitted_date:
            return None
        from datetime import date
        return (date.today() - self.submitted_date).days