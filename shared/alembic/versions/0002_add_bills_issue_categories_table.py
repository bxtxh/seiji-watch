"""Add bills_issue_categories intermediate table

Revision ID: 0002
Revises: 0001
Create Date: 2025-07-15 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create bills_issue_categories intermediate table
    op.create_table('bills_issue_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bill_id', sa.Integer(), nullable=False),
        sa.Column('issue_category_airtable_id', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('is_manual', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Add foreign key constraints
    op.create_foreign_key(
        'fk_bills_issue_categories_bill_id',
        'bills_issue_categories',
        'bills',
        ['bill_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Create indexes for performance
    op.create_index('idx_bills_categories_bill_id', 'bills_issue_categories', ['bill_id'])
    op.create_index('idx_bills_categories_airtable_id', 'bills_issue_categories', ['issue_category_airtable_id'])
    op.create_index('idx_bills_categories_confidence', 'bills_issue_categories', ['confidence_score'], postgresql_where=sa.text('confidence_score >= 0.8'))
    op.create_index('idx_bills_categories_manual', 'bills_issue_categories', ['is_manual'])

    # Composite indexes for common queries
    op.create_index('idx_bills_categories_bill_confidence', 'bills_issue_categories', ['bill_id', 'confidence_score'])
    op.create_index('idx_bills_categories_airtable_confidence', 'bills_issue_categories', ['issue_category_airtable_id', 'confidence_score'])

    # Unique constraint to prevent duplicate bill-category relationships
    op.create_unique_constraint(
        'uq_bills_issue_categories_bill_airtable',
        'bills_issue_categories',
        ['bill_id', 'issue_category_airtable_id']
    )


def downgrade() -> None:
    # Drop unique constraint
    op.drop_constraint('uq_bills_issue_categories_bill_airtable', 'bills_issue_categories', type_='unique')

    # Drop indexes
    op.drop_index('idx_bills_categories_airtable_confidence', 'bills_issue_categories')
    op.drop_index('idx_bills_categories_bill_confidence', 'bills_issue_categories')
    op.drop_index('idx_bills_categories_manual', 'bills_issue_categories')
    op.drop_index('idx_bills_categories_confidence', 'bills_issue_categories')
    op.drop_index('idx_bills_categories_airtable_id', 'bills_issue_categories')
    op.drop_index('idx_bills_categories_bill_id', 'bills_issue_categories')

    # Drop foreign key constraint
    op.drop_constraint('fk_bills_issue_categories_bill_id', 'bills_issue_categories', type_='foreignkey')

    # Drop table
    op.drop_table('bills_issue_categories')
