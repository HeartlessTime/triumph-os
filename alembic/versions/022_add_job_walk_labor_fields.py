"""Add technicians_needed and estimated_man_hours to activities

Revision ID: 022_add_job_walk_labor_fields
Revises: 021_add_estimate_due_by
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

revision = "022_add_job_walk_labor_fields"
down_revision = "021_add_estimate_due_by"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("activities", sa.Column("technicians_needed", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("estimated_man_hours", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("activities", "estimated_man_hours")
    op.drop_column("activities", "technicians_needed")
