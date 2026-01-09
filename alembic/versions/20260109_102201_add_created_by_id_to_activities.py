"""add created_by_id to activities

Revision ID: <KEEP_THE_GENERATED_ID>
Revises: 4d22e734184d
Create Date: 2026-01-09

"""
from alembic import op
import sqlalchemy as sa

revision = "<KEEP_THE_GENERATED_ID>"
down_revision = "4d22e734184d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "activities",
        sa.Column("created_by_id", sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column("activities", "created_by_id")
