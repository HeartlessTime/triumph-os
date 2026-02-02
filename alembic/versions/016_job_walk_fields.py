"""
Add job walk / estimating fields to activities table for site visits.

Revision ID: 016_job_walk_fields
Revises: 015_add_account_next_action
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

revision = "016_job_walk_fields"
down_revision = "015_add_account_next_action"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "activities",
        sa.Column("requires_estimate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "activities",
        sa.Column("scope_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("estimated_quantity", sa.String(100), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("complexity_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("estimate_needed_by", sa.Date(), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("assigned_estimator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("estimate_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade():
    op.drop_column("activities", "estimate_completed")
    op.drop_column("activities", "assigned_estimator_id")
    op.drop_column("activities", "estimate_needed_by")
    op.drop_column("activities", "complexity_notes")
    op.drop_column("activities", "estimated_quantity")
    op.drop_column("activities", "scope_summary")
    op.drop_column("activities", "requires_estimate")
