"""Bills Issue Categories relationship model."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import BaseRecord


class BillsPolicyCategory(BaseRecord):
    """Bills ↔ PolicyCategory (Airtable IssueCategories) relationship model."""

    # Basic relationship identifiers
    bill_id: str = Field(..., description="Bill identifier reference")
    policy_category_id: str = Field(
        ..., description="PolicyCategory identifier reference"
    )

    # Airtable record IDs for actual linking
    bill_record_id: Optional[str] = Field(None, description="Airtable Bills record ID")
    policy_category_record_id: Optional[str] = Field(
        None, description="Airtable IssueCategories record ID"
    )

    # Relationship metadata
    confidence_score: float = Field(
        0.8, description="Relationship confidence (0.0-1.0)"
    )
    is_manual: bool = Field(
        False, description="Whether manually created vs auto-generated"
    )
    source: str = Field("auto_migration", description="Origin of relationship")

    # Timestamps - Override base class fields to make them required
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    def __repr__(self) -> str:
        return (
            f"<BillsPolicyCategory(bill_id='{self.bill_id}', "
            f"category_id='{self.policy_category_id}', "
            f"confidence={self.confidence_score})>"
        )

    @property
    def is_high_confidence(self) -> bool:
        """Check if the relationship has high confidence (≥0.8)."""
        return self.confidence_score >= 0.8

    @property
    def is_automatically_generated(self) -> bool:
        """Check if the relationship was automatically generated (not manual)."""
        return not self.is_manual

    @classmethod
    def create_relationship(
        cls,
        bill_id: str,
        policy_category_id: str,
        confidence_score: float = 0.8,
        is_manual: bool = False,
        source: str = "auto_migration",
        bill_record_id: Optional[str] = None,
        policy_category_record_id: Optional[str] = None,
    ) -> "BillsPolicyCategory":
        """Create a new bill-category relationship."""
        now = datetime.now()
        return cls(
            bill_id=bill_id,
            policy_category_id=policy_category_id,
            bill_record_id=bill_record_id,
            policy_category_record_id=policy_category_record_id,
            confidence_score=confidence_score,
            is_manual=is_manual,
            source=source,
            created_at=now,
            updated_at=now,
        )
