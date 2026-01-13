"""
Add job_walk fields and job_notes to opportunities

Revision ID: 008_add_job_walk_fields
Revises: 007_activity_opp_nullable
Create Date: 2026-01-13
"""

from alembic import op
import sqlalchemy as sa

revision = "008_add_job_walk_fields"
down_revision = "007_activity_opp_nullable"
branch_labels = None
depends_on = None


def upgrade():
    # Add job_walk fields to opportunities table
    op.add_column(
        "opportunities",
        sa.Column("job_walk_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "opportunities",
        sa.Column("job_walk_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("job_walk_time", sa.Time(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("job_walk_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("job_notes", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("opportunities", "job_notes")
    op.drop_column("opportunities", "job_walk_notes")
    op.drop_column("opportunities", "job_walk_time")
    op.drop_column("opportunities", "job_walk_date")
    op.drop_column("opportunities", "job_walk_required")
