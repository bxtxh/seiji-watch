"""Pydantic schemas for API requests and responses."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models.bill import BillCategory, BillStatus


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )


# Party schemas
class PartyBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    name_en: str | None = Field(None, max_length=200)
    abbreviation: str | None = Field(None, max_length=10)
    description: str | None = None
    website_url: str | None = Field(None, max_length=500)
    color_code: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class PartyCreate(PartyBase):
    pass


class PartyUpdate(PartyBase):
    name: str | None = Field(None, min_length=1, max_length=100)


class PartyResponse(PartyBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Member schemas
class MemberBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    name_kana: str | None = Field(None, max_length=200)
    name_en: str | None = Field(None, max_length=200)
    house: str = Field(..., pattern=r"^(衆議院|参議院)$")
    constituency: str | None = Field(None, max_length=100)
    diet_member_id: str | None = Field(None, max_length=50)
    birth_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    gender: str | None = Field(None, max_length=10)
    first_elected: str | None = Field(None, pattern=r"^\d{4}$")
    terms_served: int | None = Field(None, ge=0)
    previous_occupations: str | None = None
    education: str | None = None
    website_url: str | None = Field(None, max_length=500)
    twitter_handle: str | None = Field(None, max_length=100)
    facebook_url: str | None = Field(None, max_length=500)


class MemberCreate(MemberBase):
    party_id: int | None = None


class MemberUpdate(MemberBase):
    name: str | None = Field(None, min_length=1, max_length=100)
    house: str | None = Field(None, pattern=r"^(衆議院|参議院)$")
    party_id: int | None = None


class MemberResponse(MemberBase):
    id: int
    party_id: int | None
    party: PartyResponse | None
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime


# Bill schemas
class BillBase(BaseSchema):
    bill_number: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=500)
    title_en: str | None = Field(None, max_length=1000)
    short_title: str | None = Field(None, max_length=200)
    summary: str | None = None
    full_text: str | None = None
    purpose: str | None = None
    category: BillCategory | None = None
    bill_type: str | None = Field(None, max_length=50)
    diet_session: str | None = Field(None, max_length=20)
    house_of_origin: str | None = Field(None, pattern=r"^(衆議院|参議院)$")
    submitter_type: str | None = Field(None, pattern=r"^(government|member)$")
    sponsoring_ministry: str | None = Field(None, max_length=100)
    diet_url: str | None = Field(None, max_length=500)
    pdf_url: str | None = Field(None, max_length=500)
    estimated_cost: str | None = Field(None, max_length=100)


class BillCreate(BillBase):
    status: BillStatus = BillStatus.BACKLOG
    submitted_date: date | None = None
    submitting_members: list[int] | None = None
    related_bills: list[int] | None = None


class BillUpdate(BillBase):
    bill_number: str | None = Field(None, min_length=1, max_length=50)
    title: str | None = Field(None, min_length=1, max_length=500)
    status: BillStatus | None = None
    submitted_date: date | None = None
    first_reading_date: date | None = None
    committee_referral_date: date | None = None
    committee_report_date: date | None = None
    final_vote_date: date | None = None
    promulgated_date: date | None = None
    submitting_members: list[int] | None = None
    related_bills: list[int] | None = None
    key_points: list[str] | None = None
    tags: list[str] | None = None
    impact_assessment: dict[str, Any] | None = None
    is_controversial: bool | None = None
    priority_level: str | None = Field(None, pattern=r"^(high|normal|low)$")


class BillResponse(BillBase):
    id: int
    status: BillStatus
    submitted_date: date | None
    first_reading_date: date | None
    committee_referral_date: date | None
    committee_report_date: date | None
    final_vote_date: date | None
    promulgated_date: date | None
    submitting_members: list[int] | None
    related_bills: list[int] | None
    ai_summary: str | None
    key_points: list[str] | None
    tags: list[str] | None
    impact_assessment: dict[str, Any] | None
    is_controversial: bool
    priority_level: str
    is_passed: bool
    is_pending: bool
    days_since_submission: int | None
    created_at: datetime
    updated_at: datetime


# Meeting schemas
class MeetingBase(BaseSchema):
    meeting_id: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=500)
    meeting_type: str = Field(..., max_length=50)
    committee_name: str | None = Field(None, max_length=200)
    diet_session: str = Field(..., max_length=20)
    house: str = Field(..., pattern=r"^(衆議院|参議院)$")
    session_number: int | None = Field(None, ge=1)
    meeting_date: datetime
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = Field(None, ge=0)
    summary: str | None = None
    meeting_notes: str | None = None
    video_url: str | None = Field(None, max_length=500)
    audio_url: str | None = Field(None, max_length=500)
    transcript_url: str | None = Field(None, max_length=500)
    participant_count: int | None = Field(None, ge=0)
    is_public: bool = True


class MeetingCreate(MeetingBase):
    agenda: list[str] | None = None
    documents_urls: list[str] | None = None


class MeetingUpdate(MeetingBase):
    meeting_id: str | None = Field(None, min_length=1, max_length=50)
    title: str | None = Field(None, min_length=1, max_length=500)
    meeting_type: str | None = Field(None, max_length=50)
    diet_session: str | None = Field(None, max_length=20)
    house: str | None = Field(None, pattern=r"^(衆議院|参議院)$")
    meeting_date: datetime | None = None
    agenda: list[str] | None = None
    documents_urls: list[str] | None = None
    is_processed: bool | None = None
    transcript_processed: bool | None = None
    stt_completed: bool | None = None
    is_cancelled: bool | None = None


class MeetingResponse(MeetingBase):
    id: int
    agenda: list[str] | None
    documents_urls: list[str] | None
    is_processed: bool
    transcript_processed: bool
    stt_completed: bool
    is_cancelled: bool
    created_at: datetime
    updated_at: datetime


# Speech schemas
class SpeechBase(BaseSchema):
    speech_order: int = Field(..., ge=1)
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: int | None = Field(None, ge=0)
    speaker_name: str | None = Field(None, max_length=200)
    speaker_title: str | None = Field(None, max_length=200)
    speaker_type: str = Field(default="member",
                              pattern=r"^(member|minister|official|other)$")
    original_text: str = Field(..., min_length=1)
    cleaned_text: str | None = None
    speech_type: str | None = Field(None, max_length=50)
    word_count: int | None = Field(None, ge=0)
    confidence_score: str | None = Field(None, max_length=10)
    is_interruption: bool = False


class SpeechCreate(SpeechBase):
    meeting_id: int
    speaker_id: int | None = None
    related_bill_id: int | None = None


class SpeechUpdate(SpeechBase):
    speech_order: int | None = Field(None, ge=1)
    original_text: str | None = Field(None, min_length=1)
    speaker_id: int | None = None
    related_bill_id: int | None = None
    summary: str | None = None
    key_points: list[str] | None = None
    topics: list[str] | None = None
    sentiment: str | None = Field(None, pattern=r"^(positive|negative|neutral)$")
    stance: str | None = Field(None, max_length=50)
    is_processed: bool | None = None
    needs_review: bool | None = None


class SpeechResponse(SpeechBase):
    id: int
    meeting_id: int
    speaker_id: int | None
    related_bill_id: int | None
    summary: str | None
    key_points: list[str] | None
    topics: list[str] | None
    sentiment: str | None
    stance: str | None
    is_processed: bool
    needs_review: bool
    display_speaker_name: str
    duration_minutes: float | None
    speaker: MemberResponse | None
    related_bill: BillResponse | None
    created_at: datetime
    updated_at: datetime


# Vote schemas
class VoteBase(BaseSchema):
    vote_result: str = Field(..., pattern=r"^(yes|no|abstain|absent|present)$")
    vote_date: datetime
    house: str = Field(..., pattern=r"^(衆議院|参議院)$")
    vote_type: str = Field(..., max_length=50)
    vote_stage: str | None = Field(None, max_length=50)
    committee_name: str | None = Field(None, max_length=200)
    total_votes: int | None = Field(None, ge=0)
    yes_votes: int | None = Field(None, ge=0)
    no_votes: int | None = Field(None, ge=0)
    abstain_votes: int | None = Field(None, ge=0)
    absent_votes: int | None = Field(None, ge=0)
    notes: str | None = None
    is_final_vote: bool = False


class VoteCreate(VoteBase):
    bill_id: int
    member_id: int


class VoteResponse(VoteBase):
    id: int
    bill_id: int
    member_id: int
    vote_result_ja: str
    bill: BillResponse | None
    member: MemberResponse | None
    created_at: datetime
    updated_at: datetime
