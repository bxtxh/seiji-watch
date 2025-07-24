"""Models for policy issues and issue tags."""


from pydantic import Field

from .base import BaseRecord


class IssueCategory(BaseRecord):
    """Issue category model for hierarchical classification (CAP-based)."""

    cap_code: str = Field(
        ..., description="CAP classification code (e.g., '13', '1305')"
    )
    layer: str = Field(..., description="Hierarchy layer (L1/L2/L3)")
    title_ja: str = Field(..., description="Japanese title")
    title_en: str | None = Field(None, description="English title")
    summary_150ja: str | None = Field(
        "", description="Japanese summary (150 chars max)"
    )
    parent_category_id: str | None = Field(
        None, description="Parent category record ID"
    )
    is_seed: bool = Field(False, description="CAP-derived seed data flag")

    def __repr__(self) -> str:
        return (
            f"<IssueCategory(cap_code='{self.cap_code}', "
            f"layer='{self.layer}', title_ja='{self.title_ja}')>"
        )

    @property
    def is_root_level(self) -> bool:
        """Check if this is a root-level category (L1)."""
        return self.layer == "L1"

    @property
    def hierarchy_depth(self) -> int:
        """Get the hierarchy depth (1 for L1, 2 for L2, 3 for L3)."""
        return int(self.layer[1]) if self.layer.startswith("L") else 0


class IssueTag(BaseRecord):
    """Issue tag model for categorizing policy issues."""

    name: str = Field(..., description="Tag name (e.g., カーボンニュートラル)")
    color_code: str = Field("#3B82F6", description="Hex color code for UI display")
    category: str = Field(
        ..., description="Tag category (環境/経済/社会保障/外交/その他)"
    )
    description: str | None = Field(None, description="Optional tag description")

    def __repr__(self) -> str:
        return f"<IssueTag(name='{self.name}', category='{self.category}')>"


class Issue(BaseRecord):
    """Policy issue model."""

    title: str = Field(..., description="Issue title (max 100 chars)")
    description: str = Field(..., description="Detailed issue description")
    priority: str = Field("medium", description="Priority level (high/medium/low)")
    status: str = Field("active", description="Issue status (active/reviewed/archived)")

    # Relationships
    related_bills: list[str] | None = Field(
        None, description="List of related Bill record IDs"
    )
    issue_tags: list[str] | None = Field(
        None, description="List of related IssueTag record IDs"
    )
    category_id: str | None = Field(
        None, description="Related IssueCategory record ID"
    )

    # Metadata
    extraction_confidence: float | None = Field(
        None, description="LLM extraction confidence score"
    )
    review_notes: str | None = Field(None, description="Admin review notes")
    is_llm_generated: bool = Field(
        False, description="Whether this issue was LLM-generated"
    )

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
