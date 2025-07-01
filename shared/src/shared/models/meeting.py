"""Models for Diet meetings and speeches."""

import enum
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer, Index, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .base import Base, TimestampMixin


class Meeting(Base, TimestampMixin):
    """Diet meeting/session model."""
    
    __tablename__ = "meetings"
    
    # Basic identification
    meeting_id = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    meeting_type = Column(String(50), nullable=False, index=True)  # 本会議/委員会/分科会
    committee_name = Column(String(200), nullable=True, index=True)  # 委員会名
    
    # Session information
    diet_session = Column(String(20), nullable=False, index=True)  # 国会回次
    house = Column(String(20), nullable=False, index=True)  # 衆議院/参議院
    session_number = Column(Integer, nullable=True)  # 第何回
    
    # Timing
    meeting_date = Column(DateTime(timezone=True), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Content
    agenda = Column(JSON, nullable=True)  # List of agenda items
    summary = Column(Text, nullable=True)
    meeting_notes = Column(Text, nullable=True)
    
    # Media and documents
    video_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    transcript_url = Column(String(500), nullable=True)
    documents_urls = Column(JSON, nullable=True)  # List of document URLs
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    transcript_processed = Column(Boolean, default=False, nullable=False)
    stt_completed = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    participant_count = Column(Integer, nullable=True)
    is_public = Column(Boolean, default=True, nullable=False)
    is_cancelled = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    speeches = relationship("Speech", back_populates="meeting", lazy="dynamic", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_meeting_date_house", "meeting_date", "house"),
        Index("idx_meeting_session_type", "diet_session", "meeting_type"),
        Index("idx_meeting_committee", "committee_name", "meeting_date"),
        Index("idx_meeting_processing", "is_processed", "transcript_processed"),
    )
    
    def __repr__(self) -> str:
        return f"<Meeting(id='{self.meeting_id}', title='{self.title[:50]}...', date='{self.meeting_date}')>"


class Speech(Base, TimestampMixin):
    """Individual speech within a meeting."""
    
    __tablename__ = "speeches"
    
    # Relationships
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    speaker_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    related_bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True, index=True)
    
    # Speech metadata
    speech_order = Column(Integer, nullable=False, index=True)  # Order within meeting
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Speaker information (for non-member speakers)
    speaker_name = Column(String(200), nullable=True)  # For ministers, officials, etc.
    speaker_title = Column(String(200), nullable=True)  # 大臣、局長、etc.
    speaker_type = Column(String(50), nullable=False, default="member", index=True)  # member/minister/official/other
    
    # Content
    original_text = Column(Text, nullable=False)  # Original transcript
    cleaned_text = Column(Text, nullable=True)  # Cleaned/processed text
    speech_type = Column(String(50), nullable=True, index=True)  # 質問/答弁/討論/etc.
    
    # LLM-generated content
    summary = Column(Text, nullable=True)  # AI-generated summary
    key_points = Column(JSON, nullable=True)  # List of key points
    topics = Column(JSON, nullable=True)  # List of topics/tags
    sentiment = Column(String(20), nullable=True)  # positive/negative/neutral
    stance = Column(String(50), nullable=True)  # 賛成/反対/中立
    
    # Vector embeddings for semantic search
    content_embedding = Column(Vector(1536), nullable=True)
    
    # Quality metrics
    word_count = Column(Integer, nullable=True)
    confidence_score = Column(String(10), nullable=True)  # STT confidence
    is_interruption = Column(Boolean, default=False, nullable=False)
    
    # Processing flags
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    needs_review = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="speeches")
    speaker = relationship("Member", back_populates="speeches")
    related_bill = relationship("Bill", back_populates="speeches")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_speech_meeting_order", "meeting_id", "speech_order"),
        Index("idx_speech_speaker_date", "speaker_id", "start_time"),
        Index("idx_speech_bill_speaker", "related_bill_id", "speaker_id"),
        Index("idx_speech_type_date", "speech_type", "start_time"),
        Index("idx_speech_content_embedding", "content_embedding"),
        Index("idx_speech_processing", "is_processed", "needs_review"),
    )
    
    def __repr__(self) -> str:
        speaker_name = self.speaker.name if self.speaker else self.speaker_name or "Unknown"
        return f"<Speech(speaker='{speaker_name}', order={self.speech_order}, meeting_id={self.meeting_id})>"
    
    @property
    def display_speaker_name(self) -> str:
        """Get the display name for the speaker."""
        if self.speaker:
            return self.speaker.display_name
        elif self.speaker_name:
            title = f" ({self.speaker_title})" if self.speaker_title else ""
            return f"{self.speaker_name}{title}"
        else:
            return "不明"
    
    @property
    def duration_minutes(self) -> float | None:
        """Get speech duration in minutes."""
        if self.duration_seconds:
            return round(self.duration_seconds / 60, 1)
        return None