"""Add next_action and next_action_due_date to accounts

Revision ID: 015_add_account_next_action
Revises: 014_add_activity_attendees
Create Date: 2026-01-30
"""
from alembic import op
import sqlalchemy as sa

revision = '015_add_account_next_action'
down_revision = '014_add_activity_attendees'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'accounts',
        sa.Column('next_action', sa.Text(), nullable=True)
    )
    op.add_column(
        'accounts',
        sa.Column('next_action_due_date', sa.Date(), nullable=True)
    )


def downgrade():
    op.drop_column('accounts', 'next_action_due_date')
    op.drop_column('accounts', 'next_action')
