"""Add estimate_due_by to activities

Revision ID: 021_add_estimate_due_by
Revises: 020_simplify_job_walks
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

revision = "021_add_estimate_due_by"
down_revision = "020_simplify_job_walks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("activities", sa.Column("estimate_due_by", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("activities", "estimate_due_by")
