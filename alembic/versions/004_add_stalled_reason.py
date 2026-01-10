"""add stalled_reason to opportunities

Revision ID: 004_stalled_reason
Revises: 003_weekly_summary_notes
Create Date: 2026-01-10
"""
from alembic import op
import sqlalchemy as sa

revision = '004_stalled_reason'
down_revision = '003_weekly_summary_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('opportunities', sa.Column('stalled_reason', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('opportunities', 'stalled_reason')
