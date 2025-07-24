"""Enhance bills table with detailed fields

Revision ID: 0003
Revises: 0002
Create Date: 2025-07-18 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    """Add detailed fields to bills table for enhanced data collection"""

    # Add new detailed content fields
    op.add_column('bills', sa.Column('bill_outline', sa.Text(), nullable=True,
                                     comment='議案要旨相当の長文情報'))
    op.add_column('bills', sa.Column('background_context', sa.Text(), nullable=True,
                                     comment='提出背景・経緯'))
    op.add_column('bills', sa.Column('expected_effects', sa.Text(), nullable=True,
                                     comment='期待される効果'))
    op.add_column(
        'bills',
        sa.Column(
            'key_provisions',
            postgresql.JSONB(
                astext_type=sa.Text()),
            nullable=True,
            comment='主要条項リスト'))
    op.add_column(
        'bills',
        sa.Column(
            'related_laws',
            postgresql.JSONB(
                astext_type=sa.Text()),
            nullable=True,
            comment='関連法律リスト'))
    op.add_column(
        'bills',
        sa.Column(
            'implementation_date',
            sa.String(
                length=10),
            nullable=True,
            comment='施行予定日'))

    # Add submission information fields
    op.add_column(
        'bills',
        sa.Column(
            'submitting_members',
            postgresql.JSONB(
                astext_type=sa.Text()),
            nullable=True,
            comment='提出議員一覧'))
    op.add_column(
        'bills',
        sa.Column(
            'supporting_members',
            postgresql.JSONB(
                astext_type=sa.Text()),
            nullable=True,
            comment='賛成議員一覧（衆議院のみ）'))
    op.add_column(
        'bills',
        sa.Column(
            'submitting_party',
            sa.String(
                length=100),
            nullable=True,
            comment='提出会派'))
    op.add_column(
        'bills',
        sa.Column(
            'sponsoring_ministry',
            sa.String(
                length=100),
            nullable=True,
            comment='主管省庁'))

    # Add process tracking fields
    op.add_column(
        'bills',
        sa.Column(
            'committee_assignments',
            postgresql.JSONB(
                astext_type=sa.Text()),
            nullable=True,
            comment='委員会付託情報'))
    op.add_column(
        'bills',
        sa.Column(
            'voting_results',
            postgresql.JSONB(
                astext_type=sa.Text()),
            nullable=True,
            comment='採決結果'))
    op.add_column(
        'bills',
        sa.Column(
            'amendments',
            postgresql.JSONB(
                astext_type=sa.Text()),
            nullable=True,
            comment='修正内容'))
    op.add_column(
        'bills',
        sa.Column(
            'inter_house_status',
            sa.String(
                length=50),
            nullable=True,
            comment='両院間の状況'))

    # Add source metadata fields
    op.add_column(
        'bills',
        sa.Column(
            'source_house',
            sa.String(
                length=10),
            nullable=True,
            comment='データ取得元議院'))
    op.add_column('bills', sa.Column('source_url', sa.String(length=500), nullable=True,
                                     comment='元データURL'))
    op.add_column('bills', sa.Column('data_quality_score', sa.Float(), nullable=True,
                                     comment='データ品質スコア'))

    # Add house of origin field if not exists
    try:
        op.add_column(
            'bills',
            sa.Column(
                'house_of_origin',
                sa.String(
                    length=10),
                nullable=True,
                comment='提出元議院'))
    except sa.exc.InvalidRequestError:
        # Column already exists, skip
        pass

    # Add diet session field if not exists
    try:
        op.add_column(
            'bills',
            sa.Column(
                'diet_session',
                sa.String(
                    length=20),
                nullable=True,
                comment='国会回次'))
    except sa.exc.InvalidRequestError:
        # Column already exists, skip
        pass

    # Create indexes for better query performance
    op.create_index('idx_bills_source_house', 'bills', ['source_house'])
    op.create_index('idx_bills_diet_session', 'bills', ['diet_session'])
    op.create_index('idx_bills_house_of_origin', 'bills', ['house_of_origin'])
    op.create_index('idx_bills_data_quality', 'bills', ['data_quality_score'])

    # Create full-text search index for bill_outline
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_bills_bill_outline_fts
        ON bills USING gin(to_tsvector('japanese', COALESCE(bill_outline, '')))
    """)

    # Create full-text search index for background_context
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_bills_background_context_fts
        ON bills USING gin(to_tsvector('japanese', COALESCE(background_context, '')))
    """)

    # Create GIN index for JSONB fields
    op.create_index(
        'idx_bills_key_provisions_gin',
        'bills',
        ['key_provisions'],
        postgresql_using='gin')
    op.create_index('idx_bills_submitting_members_gin', 'bills', [
                    'submitting_members'], postgresql_using='gin')
    op.create_index('idx_bills_committee_assignments_gin', 'bills', [
                    'committee_assignments'], postgresql_using='gin')


def downgrade():
    """Remove detailed fields from bills table"""

    # Drop indexes
    op.drop_index('idx_bills_committee_assignments_gin', table_name='bills')
    op.drop_index('idx_bills_submitting_members_gin', table_name='bills')
    op.drop_index('idx_bills_key_provisions_gin', table_name='bills')
    op.execute("DROP INDEX IF EXISTS idx_bills_background_context_fts")
    op.execute("DROP INDEX IF EXISTS idx_bills_bill_outline_fts")
    op.drop_index('idx_bills_data_quality', table_name='bills')
    op.drop_index('idx_bills_house_of_origin', table_name='bills')
    op.drop_index('idx_bills_diet_session', table_name='bills')
    op.drop_index('idx_bills_source_house', table_name='bills')

    # Remove columns
    op.drop_column('bills', 'data_quality_score')
    op.drop_column('bills', 'source_url')
    op.drop_column('bills', 'source_house')
    op.drop_column('bills', 'inter_house_status')
    op.drop_column('bills', 'amendments')
    op.drop_column('bills', 'voting_results')
    op.drop_column('bills', 'committee_assignments')
    op.drop_column('bills', 'sponsoring_ministry')
    op.drop_column('bills', 'submitting_party')
    op.drop_column('bills', 'supporting_members')
    op.drop_column('bills', 'submitting_members')
    op.drop_column('bills', 'implementation_date')
    op.drop_column('bills', 'related_laws')
    op.drop_column('bills', 'key_provisions')
    op.drop_column('bills', 'expected_effects')
    op.drop_column('bills', 'background_context')
    op.drop_column('bills', 'bill_outline')
