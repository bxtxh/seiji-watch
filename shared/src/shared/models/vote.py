"""Models for Diet voting records."""

import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Index, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class VoteResult(enum.Enum):
    """Possible voting results for a member."""
    
    YES = "yes"           # 賛成
    NO = "no"             # 反対
    ABSTAIN = "abstain"   # 棄権
    ABSENT = "absent"     # 欠席
    PRESENT = "present"   # 出席（表決せず）


class Vote(Base, TimestampMixin):
    """Individual vote record for a bill."""
    
    __tablename__ = "votes"
    
    # Relationships
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    
    # Vote details
    vote_result = Column(String(20), nullable=False, index=True)  # Store as string for flexibility
    vote_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Vote session information
    house = Column(String(20), nullable=False, index=True)  # 衆議院/参議院
    vote_type = Column(String(50), nullable=False, index=True)  # 本会議/委員会
    vote_stage = Column(String(50), nullable=True)  # 第一読会/第二読会/最終
    committee_name = Column(String(200), nullable=True)  # 委員会名（委員会採決の場合）
    
    # Vote session metadata
    total_votes = Column(Integer, nullable=True)
    yes_votes = Column(Integer, nullable=True)
    no_votes = Column(Integer, nullable=True)
    abstain_votes = Column(Integer, nullable=True)
    absent_votes = Column(Integer, nullable=True)
    
    # Additional information
    notes = Column(Text, nullable=True)  # Any special notes about this vote
    is_final_vote = Column(String(10), default=False, nullable=False)  # Is this the final vote on the bill
    
    # Relationships
    bill = relationship("Bill", back_populates="votes")
    member = relationship("Member", back_populates="votes")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_vote_bill_member", "bill_id", "member_id"),
        Index("idx_vote_date_house", "vote_date", "house"),
        Index("idx_vote_bill_result", "bill_id", "vote_result"),
        Index("idx_vote_member_result", "member_id", "vote_result"),
        Index("idx_vote_committee", "committee_name", "vote_date"),
    )
    
    def __repr__(self) -> str:
        member_name = self.member.name if self.member else "Unknown"
        return f"<Vote(member='{member_name}', result='{self.vote_result}', bill_id={self.bill_id})>"
    
    @property
    def vote_result_ja(self) -> str:
        """Get Japanese translation of vote result."""
        translations = {
            "yes": "賛成",
            "no": "反対", 
            "abstain": "棄権",
            "absent": "欠席",
            "present": "出席"
        }
        return translations.get(self.vote_result, self.vote_result)