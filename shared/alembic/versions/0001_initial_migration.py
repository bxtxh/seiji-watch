"""Initial migration - create all tables

Revision ID: 0001
Revises:
Create Date: 2025-07-01 15:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create parties table
    op.create_table('parties',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=100), nullable=False),
                    sa.Column('name_en', sa.String(length=200), nullable=True),
                    sa.Column('abbreviation', sa.String(length=10), nullable=True),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('website_url', sa.String(length=500), nullable=True),
                    sa.Column('color_code', sa.String(length=7), nullable=True),
                    sa.Column('is_active', sa.Boolean(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(
        op.f('ix_parties_created_at'),
        'parties',
        ['created_at'],
        unique=False)
    op.create_index(op.f('ix_parties_id'), 'parties', ['id'], unique=False)
    op.create_index(
        op.f('ix_parties_is_active'),
        'parties',
        ['is_active'],
        unique=False)
    op.create_index(op.f('ix_parties_name'), 'parties', ['name'], unique=True)
    op.create_index(
        op.f('ix_parties_updated_at'),
        'parties',
        ['updated_at'],
        unique=False)

    # Create members table
    op.create_table('members',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=100), nullable=False),
                    sa.Column('name_kana', sa.String(length=200), nullable=True),
                    sa.Column('name_en', sa.String(length=200), nullable=True),
                    sa.Column('party_id', sa.Integer(), nullable=True),
                    sa.Column('house', sa.String(length=20), nullable=False),
                    sa.Column('constituency', sa.String(length=100), nullable=True),
                    sa.Column('diet_member_id', sa.String(length=50), nullable=True),
                    sa.Column('birth_date', sa.String(length=10), nullable=True),
                    sa.Column('gender', sa.String(length=10), nullable=True),
                    sa.Column('first_elected', sa.String(length=10), nullable=True),
                    sa.Column('terms_served', sa.Integer(), nullable=True),
                    sa.Column('previous_occupations', sa.Text(), nullable=True),
                    sa.Column('education', sa.Text(), nullable=True),
                    sa.Column('website_url', sa.String(length=500), nullable=True),
                    sa.Column('twitter_handle', sa.String(length=100), nullable=True),
                    sa.Column('facebook_url', sa.String(length=500), nullable=True),
                    sa.Column('is_active', sa.Boolean(), nullable=False),
                    sa.Column('status', sa.String(length=20), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.ForeignKeyConstraint(['party_id'], ['parties.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index('idx_member_active_house', 'members',
                    ['is_active', 'house'], unique=False)
    op.create_index('idx_member_name_party', 'members',
                    ['name', 'party_id'], unique=False)
    op.create_index('idx_member_party_house', 'members',
                    ['party_id', 'house'], unique=False)
    op.create_index(
        op.f('ix_members_created_at'),
        'members',
        ['created_at'],
        unique=False)
    op.create_index(
        op.f('ix_members_diet_member_id'),
        'members',
        ['diet_member_id'],
        unique=True)
    op.create_index(op.f('ix_members_house'), 'members', ['house'], unique=False)
    op.create_index(op.f('ix_members_id'), 'members', ['id'], unique=False)
    op.create_index(
        op.f('ix_members_is_active'),
        'members',
        ['is_active'],
        unique=False)
    op.create_index(op.f('ix_members_name'), 'members', ['name'], unique=False)
    op.create_index(op.f('ix_members_party_id'), 'members', ['party_id'], unique=False)
    op.create_index(op.f('ix_members_status'), 'members', ['status'], unique=False)
    op.create_index(
        op.f('ix_members_updated_at'),
        'members',
        ['updated_at'],
        unique=False)

    # Create bills table
    op.create_table('bills',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('bill_number', sa.String(length=50), nullable=False),
                    sa.Column('title', sa.String(length=500), nullable=False),
                    sa.Column('title_en', sa.String(length=1000), nullable=True),
                    sa.Column('short_title', sa.String(length=200), nullable=True),
                    sa.Column('summary', sa.Text(), nullable=True),
                    sa.Column('full_text', sa.Text(), nullable=True),
                    sa.Column('purpose', sa.Text(), nullable=True),
                    sa.Column('status', sa.Enum('BACKLOG', 'UNDER_REVIEW', 'PENDING_VOTE', 'PASSED', 'REJECTED', 'WITHDRAWN', 'EXPIRED', name='billstatus'), nullable=False),
                    sa.Column('category', sa.Enum('BUDGET', 'TAXATION', 'SOCIAL_SECURITY', 'FOREIGN_AFFAIRS', 'ECONOMY', 'EDUCATION', 'ENVIRONMENT', 'INFRASTRUCTURE', 'DEFENSE', 'JUDICIARY', 'ADMINISTRATION', 'OTHER', name='billcategory'), nullable=True),
                    sa.Column('bill_type', sa.String(length=50), nullable=True),
                    sa.Column('submitted_date', sa.Date(), nullable=True),
                    sa.Column('first_reading_date', sa.Date(), nullable=True),
                    sa.Column('committee_referral_date', sa.Date(), nullable=True),
                    sa.Column('committee_report_date', sa.Date(), nullable=True),
                    sa.Column('final_vote_date', sa.Date(), nullable=True),
                    sa.Column('promulgated_date', sa.Date(), nullable=True),
                    sa.Column('diet_session', sa.String(length=20), nullable=True),
                    sa.Column('house_of_origin', sa.String(length=20), nullable=True),
                    sa.Column('submitter_type', sa.String(length=20), nullable=True),
                    sa.Column('submitting_members', sa.JSON(), nullable=True),
                    sa.Column('sponsoring_ministry', sa.String(length=100), nullable=True),
                    sa.Column('diet_url', sa.String(length=500), nullable=True),
                    sa.Column('pdf_url', sa.String(length=500), nullable=True),
                    sa.Column('related_bills', sa.JSON(), nullable=True),
                    sa.Column('ai_summary', sa.Text(), nullable=True),
                    sa.Column('key_points', sa.JSON(), nullable=True),
                    sa.Column('tags', sa.JSON(), nullable=True),
                    sa.Column('impact_assessment', sa.JSON(), nullable=True),
                    sa.Column('title_embedding', Vector(1536), nullable=True),
                    sa.Column('content_embedding', Vector(1536), nullable=True),
                    sa.Column('is_controversial', sa.Boolean(), nullable=False),
                    sa.Column('priority_level', sa.String(length=20), nullable=False),
                    sa.Column('estimated_cost', sa.String(length=100), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index('idx_bill_category_session', 'bills', [
                    'category', 'diet_session'], unique=False)
    op.create_index(
        'idx_bill_content_embedding',
        'bills',
        ['content_embedding'],
        unique=False)
    op.create_index('idx_bill_search', 'bills', ['title', 'bill_number'], unique=False)
    op.create_index(
        'idx_bill_status_date', 'bills', [
            'status', 'submitted_date'], unique=False)
    op.create_index(
        'idx_bill_timeline', 'bills', [
            'submitted_date', 'final_vote_date'], unique=False)
    op.create_index(
        'idx_bill_title_embedding',
        'bills',
        ['title_embedding'],
        unique=False)
    op.create_index(op.f('ix_bills_bill_number'), 'bills', ['bill_number'], unique=True)
    op.create_index(op.f('ix_bills_bill_type'), 'bills', ['bill_type'], unique=False)
    op.create_index(op.f('ix_bills_category'), 'bills', ['category'], unique=False)
    op.create_index(op.f('ix_bills_created_at'), 'bills', ['created_at'], unique=False)
    op.create_index(
        op.f('ix_bills_diet_session'),
        'bills',
        ['diet_session'],
        unique=False)
    op.create_index(op.f('ix_bills_id'), 'bills', ['id'], unique=False)
    op.create_index(op.f('ix_bills_status'), 'bills', ['status'], unique=False)
    op.create_index(
        op.f('ix_bills_submitted_date'),
        'bills',
        ['submitted_date'],
        unique=False)
    op.create_index(op.f('ix_bills_title'), 'bills', ['title'], unique=False)
    op.create_index(op.f('ix_bills_updated_at'), 'bills', ['updated_at'], unique=False)

    # Create meetings table
    op.create_table('meetings',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('meeting_id', sa.String(length=50), nullable=False),
                    sa.Column('title', sa.String(length=500), nullable=False),
                    sa.Column('meeting_type', sa.String(length=50), nullable=False),
                    sa.Column('committee_name', sa.String(length=200), nullable=True),
                    sa.Column('diet_session', sa.String(length=20), nullable=False),
                    sa.Column('house', sa.String(length=20), nullable=False),
                    sa.Column('session_number', sa.Integer(), nullable=True),
                    sa.Column('meeting_date', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('duration_minutes', sa.Integer(), nullable=True),
                    sa.Column('agenda', sa.JSON(), nullable=True),
                    sa.Column('summary', sa.Text(), nullable=True),
                    sa.Column('meeting_notes', sa.Text(), nullable=True),
                    sa.Column('video_url', sa.String(length=500), nullable=True),
                    sa.Column('audio_url', sa.String(length=500), nullable=True),
                    sa.Column('transcript_url', sa.String(length=500), nullable=True),
                    sa.Column('documents_urls', sa.JSON(), nullable=True),
                    sa.Column('is_processed', sa.Boolean(), nullable=False),
                    sa.Column('transcript_processed', sa.Boolean(), nullable=False),
                    sa.Column('stt_completed', sa.Boolean(), nullable=False),
                    sa.Column('participant_count', sa.Integer(), nullable=True),
                    sa.Column('is_public', sa.Boolean(), nullable=False),
                    sa.Column('is_cancelled', sa.Boolean(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index('idx_meeting_committee', 'meetings', [
                    'committee_name', 'meeting_date'], unique=False)
    op.create_index('idx_meeting_date_house', 'meetings', [
                    'meeting_date', 'house'], unique=False)
    op.create_index('idx_meeting_processing', 'meetings', [
                    'is_processed', 'transcript_processed'], unique=False)
    op.create_index('idx_meeting_session_type', 'meetings', [
                    'diet_session', 'meeting_type'], unique=False)
    op.create_index(
        op.f('ix_meetings_committee_name'),
        'meetings',
        ['committee_name'],
        unique=False)
    op.create_index(
        op.f('ix_meetings_created_at'),
        'meetings',
        ['created_at'],
        unique=False)
    op.create_index(
        op.f('ix_meetings_diet_session'),
        'meetings',
        ['diet_session'],
        unique=False)
    op.create_index(op.f('ix_meetings_house'), 'meetings', ['house'], unique=False)
    op.create_index(op.f('ix_meetings_id'), 'meetings', ['id'], unique=False)
    op.create_index(
        op.f('ix_meetings_is_processed'),
        'meetings',
        ['is_processed'],
        unique=False)
    op.create_index(
        op.f('ix_meetings_meeting_date'),
        'meetings',
        ['meeting_date'],
        unique=False)
    op.create_index(
        op.f('ix_meetings_meeting_id'),
        'meetings',
        ['meeting_id'],
        unique=True)
    op.create_index(
        op.f('ix_meetings_meeting_type'),
        'meetings',
        ['meeting_type'],
        unique=False)
    op.create_index(op.f('ix_meetings_title'), 'meetings', ['title'], unique=False)
    op.create_index(
        op.f('ix_meetings_updated_at'),
        'meetings',
        ['updated_at'],
        unique=False)

    # Create speeches table
    op.create_table('speeches',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('meeting_id', sa.Integer(), nullable=False),
                    sa.Column('speaker_id', sa.Integer(), nullable=True),
                    sa.Column('related_bill_id', sa.Integer(), nullable=True),
                    sa.Column('speech_order', sa.Integer(), nullable=False),
                    sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('duration_seconds', sa.Integer(), nullable=True),
                    sa.Column('speaker_name', sa.String(length=200), nullable=True),
                    sa.Column('speaker_title', sa.String(length=200), nullable=True),
                    sa.Column('speaker_type', sa.String(length=50), nullable=False),
                    sa.Column('original_text', sa.Text(), nullable=False),
                    sa.Column('cleaned_text', sa.Text(), nullable=True),
                    sa.Column('speech_type', sa.String(length=50), nullable=True),
                    sa.Column('summary', sa.Text(), nullable=True),
                    sa.Column('key_points', sa.JSON(), nullable=True),
                    sa.Column('topics', sa.JSON(), nullable=True),
                    sa.Column('sentiment', sa.String(length=20), nullable=True),
                    sa.Column('stance', sa.String(length=50), nullable=True),
                    sa.Column('content_embedding', Vector(1536), nullable=True),
                    sa.Column('word_count', sa.Integer(), nullable=True),
                    sa.Column('confidence_score', sa.String(length=10), nullable=True),
                    sa.Column('is_interruption', sa.Boolean(), nullable=False),
                    sa.Column('is_processed', sa.Boolean(), nullable=False),
                    sa.Column('needs_review', sa.Boolean(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ),
                    sa.ForeignKeyConstraint(['related_bill_id'], ['bills.id'], ),
                    sa.ForeignKeyConstraint(['speaker_id'], ['members.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index('idx_speech_bill_speaker', 'speeches', [
                    'related_bill_id', 'speaker_id'], unique=False)
    op.create_index(
        'idx_speech_content_embedding',
        'speeches',
        ['content_embedding'],
        unique=False)
    op.create_index('idx_speech_meeting_order', 'speeches', [
                    'meeting_id', 'speech_order'], unique=False)
    op.create_index('idx_speech_processing', 'speeches', [
                    'is_processed', 'needs_review'], unique=False)
    op.create_index('idx_speech_speaker_date', 'speeches', [
                    'speaker_id', 'start_time'], unique=False)
    op.create_index('idx_speech_type_date', 'speeches', [
                    'speech_type', 'start_time'], unique=False)
    op.create_index(
        op.f('ix_speeches_created_at'),
        'speeches',
        ['created_at'],
        unique=False)
    op.create_index(op.f('ix_speeches_id'), 'speeches', ['id'], unique=False)
    op.create_index(
        op.f('ix_speeches_is_processed'),
        'speeches',
        ['is_processed'],
        unique=False)
    op.create_index(
        op.f('ix_speeches_meeting_id'),
        'speeches',
        ['meeting_id'],
        unique=False)
    op.create_index(
        op.f('ix_speeches_related_bill_id'),
        'speeches',
        ['related_bill_id'],
        unique=False)
    op.create_index(
        op.f('ix_speeches_speaker_id'),
        'speeches',
        ['speaker_id'],
        unique=False)
    op.create_index(
        op.f('ix_speeches_speaker_type'),
        'speeches',
        ['speaker_type'],
        unique=False)
    op.create_index(
        op.f('ix_speeches_speech_order'),
        'speeches',
        ['speech_order'],
        unique=False)
    op.create_index(
        op.f('ix_speeches_speech_type'),
        'speeches',
        ['speech_type'],
        unique=False)
    op.create_index(
        op.f('ix_speeches_updated_at'),
        'speeches',
        ['updated_at'],
        unique=False)

    # Create votes table
    op.create_table('votes',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('bill_id', sa.Integer(), nullable=False),
                    sa.Column('member_id', sa.Integer(), nullable=False),
                    sa.Column('vote_result', sa.String(length=20), nullable=False),
                    sa.Column('vote_date', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('house', sa.String(length=20), nullable=False),
                    sa.Column('vote_type', sa.String(length=50), nullable=False),
                    sa.Column('vote_stage', sa.String(length=50), nullable=True),
                    sa.Column('committee_name', sa.String(length=200), nullable=True),
                    sa.Column('total_votes', sa.Integer(), nullable=True),
                    sa.Column('yes_votes', sa.Integer(), nullable=True),
                    sa.Column('no_votes', sa.Integer(), nullable=True),
                    sa.Column('abstain_votes', sa.Integer(), nullable=True),
                    sa.Column('absent_votes', sa.Integer(), nullable=True),
                    sa.Column('notes', sa.Text(), nullable=True),
                    sa.Column('is_final_vote', sa.String(length=10), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                    sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
                    sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(
        'idx_vote_bill_member', 'votes', [
            'bill_id', 'member_id'], unique=False)
    op.create_index(
        'idx_vote_bill_result', 'votes', [
            'bill_id', 'vote_result'], unique=False)
    op.create_index(
        'idx_vote_committee', 'votes', [
            'committee_name', 'vote_date'], unique=False)
    op.create_index(
        'idx_vote_date_house', 'votes', [
            'vote_date', 'house'], unique=False)
    op.create_index(
        'idx_vote_member_result', 'votes', [
            'member_id', 'vote_result'], unique=False)
    op.create_index(op.f('ix_votes_bill_id'), 'votes', ['bill_id'], unique=False)
    op.create_index(op.f('ix_votes_created_at'), 'votes', ['created_at'], unique=False)
    op.create_index(op.f('ix_votes_house'), 'votes', ['house'], unique=False)
    op.create_index(op.f('ix_votes_id'), 'votes', ['id'], unique=False)
    op.create_index(op.f('ix_votes_member_id'), 'votes', ['member_id'], unique=False)
    op.create_index(op.f('ix_votes_updated_at'), 'votes', ['updated_at'], unique=False)
    op.create_index(op.f('ix_votes_vote_date'), 'votes', ['vote_date'], unique=False)
    op.create_index(
        op.f('ix_votes_vote_result'),
        'votes',
        ['vote_result'],
        unique=False)
    op.create_index(op.f('ix_votes_vote_type'), 'votes', ['vote_type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('votes')
    op.drop_table('speeches')
    op.drop_table('meetings')
    op.drop_table('bills')
    op.drop_table('members')
    op.drop_table('parties')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS billcategory")
    op.execute("DROP TYPE IF EXISTS billstatus")
