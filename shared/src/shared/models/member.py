"""Models for Diet members and political parties."""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class Party(Base, TimestampMixin):
    """Political party model."""
    
    __tablename__ = "parties"
    
    name = Column(String(100), nullable=False, unique=True, index=True)
    name_en = Column(String(200), nullable=True)  # English name
    abbreviation = Column(String(10), nullable=True)  # 略称
    description = Column(Text, nullable=True)
    website_url = Column(String(500), nullable=True)
    color_code = Column(String(7), nullable=True)  # Hex color for UI
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    members = relationship("Member", back_populates="party", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<Party(name='{self.name}')>"


class Member(Base, TimestampMixin):
    """Diet member model."""
    
    __tablename__ = "members"
    
    # Basic information
    name = Column(String(100), nullable=False, index=True)
    name_kana = Column(String(200), nullable=True)  # ひらがな読み
    name_en = Column(String(200), nullable=True)  # English name
    
    # Political information
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    house = Column(String(20), nullable=False, index=True)  # 衆議院/参議院
    constituency = Column(String(100), nullable=True)  # 選挙区
    diet_member_id = Column(String(50), nullable=True, unique=True, index=True)  # 国会議員ID
    
    # Personal information
    birth_date = Column(String(10), nullable=True)  # YYYY-MM-DD format
    gender = Column(String(10), nullable=True)
    
    # Career information
    first_elected = Column(String(10), nullable=True)  # 初当選年
    terms_served = Column(Integer, nullable=True)  # 当選回数
    previous_occupations = Column(Text, nullable=True)  # 前職
    education = Column(Text, nullable=True)  # 学歴
    
    # Contact and web presence
    website_url = Column(String(500), nullable=True)
    twitter_handle = Column(String(100), nullable=True)
    facebook_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    status = Column(String(20), default="active", nullable=False, index=True)  # active, inactive, deceased
    
    # Relationships
    party = relationship("Party", back_populates="members")
    speeches = relationship("Speech", back_populates="speaker", lazy="dynamic")
    votes = relationship("Vote", back_populates="member", lazy="dynamic")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_member_party_house", "party_id", "house"),
        Index("idx_member_name_party", "name", "party_id"),
        Index("idx_member_active_house", "is_active", "house"),
    )
    
    def __repr__(self) -> str:
        return f"<Member(name='{self.name}', party='{self.party.name if self.party else None}', house='{self.house}')>"
    
    @property
    def display_name(self) -> str:
        """Get display name with party affiliation."""
        party_name = self.party.abbreviation if self.party and self.party.abbreviation else (self.party.name if self.party else "無所属")
        return f"{self.name} ({party_name})"