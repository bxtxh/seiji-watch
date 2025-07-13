"""Pydantic schemas for API requests and responses."""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from ..models.bill import BillStatus, BillCategory


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
    name_en: Optional[str] = Field(None, max_length=200)
    abbreviation: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    website_url: Optional[str] = Field(None, max_length=500)
    color_code: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class PartyCreate(PartyBase):
    pass


class PartyUpdate(PartyBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class PartyResponse(PartyBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Member schemas
class MemberBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    name_kana: Optional[str] = Field(None, max_length=200)
    name_en: Optional[str] = Field(None, max_length=200)
    house: str = Field(..., pattern=r"^(衆議院|参議院)$")
    constituency: Optional[str] = Field(None, max_length=100)
    diet_member_id: Optional[str] = Field(None, max_length=50)
    birth_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    gender: Optional[str] = Field(None, max_length=10)
    first_elected: Optional[str] = Field(None, pattern=r"^\d{4}$")
    terms_served: Optional[int] = Field(None, ge=0)
    previous_occupations: Optional[str] = None
    education: Optional[str] = None
    website_url: Optional[str] = Field(None, max_length=500)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    facebook_url: Optional[str] = Field(None, max_length=500)


class MemberCreate(MemberBase):
    party_id: Optional[int] = None


class MemberUpdate(MemberBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    house: Optional[str] = Field(None, pattern=r"^(衆議院|参議院)$")
    party_id: Optional[int] = None


class MemberResponse(MemberBase):
    id: int
    party_id: Optional[int]
    party: Optional[PartyResponse]
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime


# Bill schemas
class BillBase(BaseSchema):
    bill_number: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=500)
    title_en: Optional[str] = Field(None, max_length=1000)
    short_title: Optional[str] = Field(None, max_length=200)
    summary: Optional[str] = None
    full_text: Optional[str] = None
    purpose: Optional[str] = None
    category: Optional[BillCategory] = None
    bill_type: Optional[str] = Field(None, max_length=50)
    diet_session: Optional[str] = Field(None, max_length=20)
    house_of_origin: Optional[str] = Field(None, pattern=r"^(衆議院|参議院)$")
    submitter_type: Optional[str] = Field(None, pattern=r"^(government|member)$")
    sponsoring_ministry: Optional[str] = Field(None, max_length=100)
    diet_url: Optional[str] = Field(None, max_length=500)
    pdf_url: Optional[str] = Field(None, max_length=500)
    estimated_cost: Optional[str] = Field(None, max_length=100)


class BillCreate(BillBase):
    status: BillStatus = BillStatus.BACKLOG
    submitted_date: Optional[date] = None
    submitting_members: Optional[List[int]] = None
    related_bills: Optional[List[int]] = None


class BillUpdate(BillBase):
    bill_number: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[BillStatus] = None
    submitted_date: Optional[date] = None
    first_reading_date: Optional[date] = None
    committee_referral_date: Optional[date] = None
    committee_report_date: Optional[date] = None
    final_vote_date: Optional[date] = None
    promulgated_date: Optional[date] = None
    submitting_members: Optional[List[int]] = None
    related_bills: Optional[List[int]] = None
    key_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    impact_assessment: Optional[Dict[str, Any]] = None
    is_controversial: Optional[bool] = None
    priority_level: Optional[str] = Field(None, pattern=r"^(high|normal|low)$")


class BillResponse(BillBase):
    id: int
    status: BillStatus
    submitted_date: Optional[date]
    first_reading_date: Optional[date]
    committee_referral_date: Optional[date]
    committee_report_date: Optional[date]
    final_vote_date: Optional[date]
    promulgated_date: Optional[date]
    submitting_members: Optional[List[int]]
    related_bills: Optional[List[int]]
    ai_summary: Optional[str]
    key_points: Optional[List[str]]
    tags: Optional[List[str]]
    impact_assessment: Optional[Dict[str, Any]]
    is_controversial: bool
    priority_level: str
    is_passed: bool
    is_pending: bool
    days_since_submission: Optional[int]
    created_at: datetime
    updated_at: datetime


# Meeting schemas
class MeetingBase(BaseSchema):
    meeting_id: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=500)
    meeting_type: str = Field(..., max_length=50)
    committee_name: Optional[str] = Field(None, max_length=200)
    diet_session: str = Field(..., max_length=20)
    house: str = Field(..., pattern=r"^(衆議院|参議院)$")
    session_number: Optional[int] = Field(None, ge=1)
    meeting_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    summary: Optional[str] = None
    meeting_notes: Optional[str] = None
    video_url: Optional[str] = Field(None, max_length=500)
    audio_url: Optional[str] = Field(None, max_length=500)
    transcript_url: Optional[str] = Field(None, max_length=500)
    participant_count: Optional[int] = Field(None, ge=0)
    is_public: bool = True


class MeetingCreate(MeetingBase):
    agenda: Optional[List[str]] = None
    documents_urls: Optional[List[str]] = None


class MeetingUpdate(MeetingBase):
    meeting_id: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    meeting_type: Optional[str] = Field(None, max_length=50)
    diet_session: Optional[str] = Field(None, max_length=20)
    house: Optional[str] = Field(None, pattern=r"^(衆議院|参議院)$")
    meeting_date: Optional[datetime] = None
    agenda: Optional[List[str]] = None
    documents_urls: Optional[List[str]] = None
    is_processed: Optional[bool] = None
    transcript_processed: Optional[bool] = None
    stt_completed: Optional[bool] = None
    is_cancelled: Optional[bool] = None


class MeetingResponse(MeetingBase):
    id: int
    agenda: Optional[List[str]]
    documents_urls: Optional[List[str]]
    is_processed: bool
    transcript_processed: bool
    stt_completed: bool
    is_cancelled: bool
    created_at: datetime
    updated_at: datetime


# Speech schemas
class SpeechBase(BaseSchema):
    speech_order: int = Field(..., ge=1)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    speaker_name: Optional[str] = Field(None, max_length=200)
    speaker_title: Optional[str] = Field(None, max_length=200)
    speaker_type: str = Field(default="member", pattern=r"^(member|minister|official|other)$")
    original_text: str = Field(..., min_length=1)
    cleaned_text: Optional[str] = None
    speech_type: Optional[str] = Field(None, max_length=50)
    word_count: Optional[int] = Field(None, ge=0)
    confidence_score: Optional[str] = Field(None, max_length=10)
    is_interruption: bool = False


class SpeechCreate(SpeechBase):
    meeting_id: int
    speaker_id: Optional[int] = None
    related_bill_id: Optional[int] = None


class SpeechUpdate(SpeechBase):
    speech_order: Optional[int] = Field(None, ge=1)
    original_text: Optional[str] = Field(None, min_length=1)
    speaker_id: Optional[int] = None
    related_bill_id: Optional[int] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    sentiment: Optional[str] = Field(None, pattern=r"^(positive|negative|neutral)$")
    stance: Optional[str] = Field(None, max_length=50)
    is_processed: Optional[bool] = None
    needs_review: Optional[bool] = None


class SpeechResponse(SpeechBase):
    id: int
    meeting_id: int
    speaker_id: Optional[int]
    related_bill_id: Optional[int]
    summary: Optional[str]
    key_points: Optional[List[str]]
    topics: Optional[List[str]]
    sentiment: Optional[str]
    stance: Optional[str]
    is_processed: bool
    needs_review: bool
    display_speaker_name: str
    duration_minutes: Optional[float]
    speaker: Optional[MemberResponse]
    related_bill: Optional[BillResponse]
    created_at: datetime
    updated_at: datetime


# Vote schemas
class VoteBase(BaseSchema):
    vote_result: str = Field(..., pattern=r"^(yes|no|abstain|absent|present)$")
    vote_date: datetime
    house: str = Field(..., pattern=r"^(衆議院|参議院)$")
    vote_type: str = Field(..., max_length=50)
    vote_stage: Optional[str] = Field(None, max_length=50)
    committee_name: Optional[str] = Field(None, max_length=200)
    total_votes: Optional[int] = Field(None, ge=0)
    yes_votes: Optional[int] = Field(None, ge=0)
    no_votes: Optional[int] = Field(None, ge=0)
    abstain_votes: Optional[int] = Field(None, ge=0)
    absent_votes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    is_final_vote: bool = False


class VoteCreate(VoteBase):
    bill_id: int
    member_id: int


class VoteResponse(VoteBase):
    id: int
    bill_id: int
    member_id: int
    vote_result_ja: str
    bill: Optional[BillResponse]
    member: Optional[MemberResponse]
    created_at: datetime
    updated_at: datetime