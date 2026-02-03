"""
Create walk_segments table for field walk activities.

Revision ID: 018_walk_segments
Revises: 017_est_completed_at
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

revision = "018_walk_segments"
down_revision = "017_est_completed_at"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "walk_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "activity_id",
            sa.Integer(),
            sa.ForeignKey("activities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("location_name", sa.String(255), nullable=False),
        sa.Column("segment_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity_count", sa.Integer(), nullable=True),
        sa.Column("quantity_label", sa.String(100), nullable=True),
        sa.Column("photo_notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade():
    op.drop_table("walk_segments")
