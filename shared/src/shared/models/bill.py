"""Models for Diet bills and legislation."""

import enum
from datetime import date
from typing import Any

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
    title_en: str | None = Field(None, description="English title")
    short_title: str | None = Field(None, description="Short title/abbreviation")

    # Content
    summary: str | None = Field(None, description="Bill summary")
    full_text: str | None = Field(None, description="Full bill text")
    purpose: str | None = Field(None, description="Purpose of the bill")

    # Enhanced detailed content (新規追加)
    bill_outline: str | None = Field(None, description="議案要旨相当の長文情報")
    background_context: str | None = Field(None, description="提出背景・経緯")
    expected_effects: str | None = Field(None, description="期待される効果")
    key_provisions: list[str] | None = Field(None, description="主要条項リスト")
    related_laws: list[str] | None = Field(None, description="関連法律リスト")
    implementation_date: str | None = Field(None, description="施行予定日")

    # Classification
    status: BillStatus = Field(BillStatus.BACKLOG, description="Current bill status")
    category: BillCategory | None = Field(None, description="Bill category")
    bill_type: str | None = Field(None, description="Bill type (government/member)")

    # Timeline
    submitted_date: str | None = Field(
        None, description="Submission date (YYYY-MM-DD)"
    )
    first_reading_date: str | None = Field(None, description="First reading date")
    committee_referral_date: str | None = Field(
        None, description="Committee referral date"
    )
    committee_report_date: str | None = Field(
        None, description="Committee report date"
    )
    final_vote_date: str | None = Field(None, description="Final vote date")
    promulgated_date: str | None = Field(None, description="Promulgation date")

    # Session information
    diet_session: str | None = Field(None, description="Diet session number")
    house_of_origin: str | None = Field(None, description="House of origin")

    # Submitter information (拡張)
    submitter_type: str | None = Field(None, description="Submitter type")
    submitting_members: list[str] | None = Field(
        None, description="List of submitting member IDs"
    )
    supporting_members: list[str] | None = Field(
        None, description="賛成議員一覧（衆議院のみ）"
    )
    submitting_party: str | None = Field(None, description="提出会派")
    sponsoring_ministry: str | None = Field(None, description="Sponsoring ministry")

    # URLs and references
    diet_url: str | None = Field(None, description="Diet website URL")
    pdf_url: str | None = Field(None, description="PDF document URL")
    related_bills: list[str] | None = Field(
        None, description="List of related bill IDs"
    )

    # Process tracking (新規追加)
    committee_assignments: dict[str, Any] | None = Field(
        None, description="委員会付託情報"
    )
    voting_results: dict[str, Any] | None = Field(None, description="採決結果")
    amendments: list[dict[str, Any]] | None = Field(None, description="修正内容")
    inter_house_status: str | None = Field(None, description="両院間の状況")

    # LLM-generated content
    ai_summary: str | None = Field(None, description="AI-generated summary")
    key_points: list[str] | None = Field(None, description="List of key points")
    tags: list[str] | None = Field(None, description="List of tags")
    impact_assessment: dict[str, Any] | None = Field(
        None, description="AI impact analysis"
    )

    # Metadata (拡張)
    is_controversial: bool = Field(
        False, description="Whether the bill is controversial"
    )
    priority_level: str = Field(
        "normal", description="Priority level (high/normal/low)"
    )
    estimated_cost: str | None = Field(None, description="Estimated cost")

    # Source metadata (新規追加)
    source_house: str | None = Field(None, description="データ取得元議院")
    source_url: str | None = Field(None, description="元データURL")
    data_quality_score: float | None = Field(None, description="データ品質スコア")

    # Issue Management
    related_issues: list[str] | None = Field(
        None, description="List of related Issue record IDs"
    )
    issue_tags: list[str] | None = Field(
        None, description="List of related IssueTag record IDs"
    )

    # SQLAlchemy relationships (when used as SQLAlchemy model)
    # Note: This will be available when the model is used with SQLAlchemy
    # issue_category_relationships = relationship(
    #     "BillsIssueCategories", back_populates="bill"
    # )

    def __repr__(self) -> str:
        return (
            f"<Bill(number='{self.bill_number}', "
            f"title='{self.title[:50]}...', status='{self.status.value}')>"
        )

    @property
    def is_passed(self) -> bool:
        """Check if the bill has been passed."""
        return self.status == BillStatus.PASSED

    @property
    def is_pending(self) -> bool:
        """Check if the bill is still in progress."""
        return self.status in [
            BillStatus.BACKLOG, BillStatus.UNDER_REVIEW, BillStatus.PENDING_VOTE
        ]

    @property
    def days_since_submission(self) -> int | None:
        """Calculate days since bill submission."""
        if not self.submitted_date:
            return None
        try:
            from datetime import datetime
            submitted = datetime.strptime(self.submitted_date, "%Y-%m-%d").date()
            return (date.today() - submitted).days
        except ValueError:
            return None
