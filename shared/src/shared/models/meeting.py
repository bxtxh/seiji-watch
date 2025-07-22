"""Models for Diet meetings and speeches."""

from pydantic import Field

from .base import BaseRecord


class Meeting(BaseRecord):
    """Diet meeting/session model."""

    # Basic identification
    meeting_id: str = Field(..., description="Unique meeting identifier")
    title: str = Field(..., description="Meeting title")
    meeting_type: str = Field(..., description="Meeting type (本会議/委員会/分科会)")
    committee_name: str | None = Field(None, description="Committee name")

    # Session information
    diet_session: str = Field(..., description="Diet session number")
    house: str = Field(..., description="House (衆議院/参議院)")
    session_number: int | None = Field(None, description="Session number")

    # Timing
    meeting_date: str = Field(..., description="Meeting date (ISO format)")
    start_time: str | None = Field(None, description="Start time (ISO format)")
    end_time: str | None = Field(None, description="End time (ISO format)")
    duration_minutes: int | None = Field(None, description="Duration in minutes")

    # Content
    agenda: list[str] | None = Field(None, description="List of agenda items")
    summary: str | None = Field(None, description="Meeting summary")
    meeting_notes: str | None = Field(None, description="Meeting notes")

    # Media and documents
    video_url: str | None = Field(None, description="Video URL")
    audio_url: str | None = Field(None, description="Audio URL")
    transcript_url: str | None = Field(None, description="Transcript URL")
    documents_urls: list[str] | None = Field(None, description="List of document URLs")

    # Processing status
    is_processed: bool = Field(False, description="Whether meeting is processed")
    transcript_processed: bool = Field(
        False, description="Whether transcript is processed"
    )
    stt_completed: bool = Field(False, description="Whether STT is completed")

    # Metadata
    participant_count: int | None = Field(None, description="Number of participants")
    is_public: bool = Field(True, description="Whether meeting is public")
    is_cancelled: bool = Field(False, description="Whether meeting is cancelled")

    def __repr__(self) -> str:
        return f"<Meeting(id='{self.meeting_id}', title='{self.title[:50]}...', date='{self.meeting_date}')>"


class Speech(BaseRecord):
    """Individual speech within a meeting."""

    # Relationships
    meeting_id: str = Field(..., description="Airtable Meeting record ID")
    speaker_id: str | None = Field(None, description="Airtable Member record ID")
    related_bill_id: str | None = Field(None, description="Airtable Bill record ID")

    # Speech metadata
    speech_order: int = Field(..., description="Order within meeting")
    start_time: str | None = Field(None, description="Speech start time (ISO format)")
    end_time: str | None = Field(None, description="Speech end time (ISO format)")
    duration_seconds: int | None = Field(None, description="Duration in seconds")

    # Speaker information (for non-member speakers)
    speaker_name: str | None = Field(None, description="Speaker name (for non-members)")
    speaker_title: str | None = Field(None, description="Speaker title")
    speaker_type: str = Field(
        "member", description="Speaker type (member/minister/official/other)"
    )

    # Content
    original_text: str = Field(..., description="Original transcript text")
    cleaned_text: str | None = Field(None, description="Cleaned/processed text")
    speech_type: str | None = Field(None, description="Speech type (質問/答弁/討論)")

    # LLM-generated content
    summary: str | None = Field(None, description="AI-generated summary")
    key_points: list[str] | None = Field(None, description="List of key points")
    topics: list[str] | None = Field(None, description="List of topics/tags")
    sentiment: str | None = Field(
        None, description="Sentiment (positive/negative/neutral)"
    )
    stance: str | None = Field(None, description="Stance (賛成/反対/中立)")

    # Quality metrics
    word_count: int | None = Field(None, description="Word count")
    confidence_score: str | None = Field(None, description="STT confidence score")
    is_interruption: bool = Field(False, description="Whether this is an interruption")

    # Processing flags
    is_processed: bool = Field(False, description="Whether speech is processed")
    needs_review: bool = Field(False, description="Whether speech needs review")

    def __repr__(self) -> str:
        speaker_name = self.speaker_name or "Unknown"
        return f"<Speech(speaker='{speaker_name}', order={self.speech_order}, meeting_id={self.meeting_id})>"

    @property
    def display_speaker_name(self) -> str:
        """Get the display name for the speaker."""
        if self.speaker_name:
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
