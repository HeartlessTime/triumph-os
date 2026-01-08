"""add meeting_briefs table for AI research caching

Revision ID: 006_add_meeting_briefs_table
Revises: 005_add_opportunity_gcs_quicklinks
Create Date: 2026-01-08 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_add_meeting_briefs_table'
down_revision = '005_add_opportunity_gcs_quicklinks'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'meeting_briefs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('brief_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_meeting_briefs_account_id', 'meeting_briefs', ['account_id'])


def downgrade():
    op.drop_index('ix_meeting_briefs_account_id', table_name='meeting_briefs')
    op.drop_table('meeting_briefs')
