"""Models for Diet voting records."""

import enum

from pydantic import Field

from .base import BaseRecord


class VoteResult(enum.Enum):
    """Possible voting results for a member."""

    YES = "yes"  # 賛成
    NO = "no"  # 反対
    ABSTAIN = "abstain"  # 棄権
    ABSENT = "absent"  # 欠席
    PRESENT = "present"  # 出席（表決せず）


class Vote(BaseRecord):
    """Individual vote record for a bill."""

    # Relationships
    bill_id: str = Field(..., description="Airtable Bill record ID")
    member_id: str = Field(..., description="Airtable Member record ID")

    # Vote details
    vote_result: str = Field(
        ..., description="Vote result (yes/no/abstain/absent/present)"
    )
    vote_date: str = Field(..., description="Vote date (ISO format)")

    # Vote session information
    house: str = Field(..., description="House (衆議院/参議院)")
    vote_type: str = Field(..., description="Vote type (本会議/委員会)")
    vote_stage: str | None = Field(
        None, description="Vote stage (第一読会/第二読会/最終)"
    )
    committee_name: str | None = Field(
        None, description="Committee name (for committee votes)"
    )

    # Vote session metadata
    total_votes: int | None = Field(None, description="Total number of votes")
    yes_votes: int | None = Field(None, description="Number of yes votes")
    no_votes: int | None = Field(None, description="Number of no votes")
    abstain_votes: int | None = Field(None, description="Number of abstain votes")
    absent_votes: int | None = Field(None, description="Number of absent votes")

    # Additional information
    notes: str | None = Field(None, description="Special notes about this vote")
    is_final_vote: bool = Field(
        False, description="Whether this is the final vote on the bill"
    )

    def __repr__(self) -> str:
        return (
            f"<Vote(result='{self.vote_result}', "
            f"bill_id={self.bill_id}, member_id={self.member_id})>"
        )

    @property
    def vote_result_ja(self) -> str:
        """Get Japanese translation of vote result."""
        translations = {
            "yes": "賛成",
            "no": "反対",
            "abstain": "棄権",
            "absent": "欠席",
            "present": "出席",
        }
        return translations.get(self.vote_result, self.vote_result)
