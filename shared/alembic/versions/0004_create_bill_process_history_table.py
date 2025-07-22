"""Create bill process history table

Revision ID: 0004
Revises: 0003
Create Date: 2025-07-18 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    """Create bill_process_history table for tracking bill progress"""

    # Create bill_process_history table
    op.create_table(
        "bill_process_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False, comment="審議段階"),
        sa.Column("house", sa.String(length=10), nullable=False, comment="議院"),
        sa.Column("committee", sa.String(length=100), nullable=True, comment="委員会"),
        sa.Column(
            "action_date", sa.DateTime(timezone=True), nullable=False, comment="実施日"
        ),
        sa.Column(
            "action_type",
            sa.String(length=50),
            nullable=False,
            comment="アクション種別",
        ),
        sa.Column("result", sa.String(length=50), nullable=True, comment="結果"),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="詳細情報",
        ),
        sa.Column("notes", sa.Text(), nullable=True, comment="備考"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
    )

    # Create indexes for better query performance
    op.create_index(
        "idx_bill_process_history_bill_id", "bill_process_history", ["bill_id"]
    )
    op.create_index("idx_bill_process_history_stage", "bill_process_history", ["stage"])
    op.create_index("idx_bill_process_history_house", "bill_process_history", ["house"])
    op.create_index(
        "idx_bill_process_history_action_date", "bill_process_history", ["action_date"]
    )
    op.create_index(
        "idx_bill_process_history_action_type", "bill_process_history", ["action_type"]
    )

    # Create composite index for common queries
    op.create_index(
        "idx_bill_process_history_bill_stage_date",
        "bill_process_history",
        ["bill_id", "stage", "action_date"],
    )
    op.create_index(
        "idx_bill_process_history_house_date",
        "bill_process_history",
        ["house", "action_date"],
    )

    # Create GIN index for JSONB details field
    op.create_index(
        "idx_bill_process_history_details_gin",
        "bill_process_history",
        ["details"],
        postgresql_using="gin",
    )


def downgrade():
    """Drop bill_process_history table"""

    # Drop indexes
    op.drop_index(
        "idx_bill_process_history_details_gin", table_name="bill_process_history"
    )
    op.drop_index(
        "idx_bill_process_history_house_date", table_name="bill_process_history"
    )
    op.drop_index(
        "idx_bill_process_history_bill_stage_date", table_name="bill_process_history"
    )
    op.drop_index(
        "idx_bill_process_history_action_type", table_name="bill_process_history"
    )
    op.drop_index(
        "idx_bill_process_history_action_date", table_name="bill_process_history"
    )
    op.drop_index("idx_bill_process_history_house", table_name="bill_process_history")
    op.drop_index("idx_bill_process_history_stage", table_name="bill_process_history")
    op.drop_index("idx_bill_process_history_bill_id", table_name="bill_process_history")

    # Drop table
    op.drop_table("bill_process_history")
