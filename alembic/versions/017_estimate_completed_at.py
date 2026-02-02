"""
Add estimate_completed_at date field to activities table.

Revision ID: 017_est_completed_at
Revises: 016_job_walk_fields
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

revision = "017_est_completed_at"
down_revision = "016_job_walk_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "activities",
        sa.Column("estimate_completed_at", sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column("activities", "estimate_completed_at")
