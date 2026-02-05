"""
Add commission_entries table for commission tracking.

Revision ID: 017_add_commission_entries
Revises: 016_job_walk_fields
Create Date: 2026-02-05
"""

from alembic import op
import sqlalchemy as sa

revision = "017_add_commission_entries"
down_revision = "016_job_walk_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commission_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column("job_number", sa.String(100), nullable=True),
        sa.Column("contact", sa.String(255), nullable=True),
        sa.Column("job_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("exported_month", sa.String(7), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("commission_entries")
