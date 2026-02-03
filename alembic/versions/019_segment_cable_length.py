"""
Add estimated_cable_length to walk_segments table.

Revision ID: 019_segment_cable_len
Revises: 018_walk_segments
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

revision = "019_segment_cable_len"
down_revision = "018_walk_segments"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "walk_segments",
        sa.Column("estimated_cable_length", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("walk_segments", "estimated_cable_length")
