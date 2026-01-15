"""add account_type field to accounts

Revision ID: 011_add_account_type
Revises: 010_user_summary_suppression
Create Date: 2026-01-15
"""
from alembic import op
import sqlalchemy as sa

revision = '011_add_account_type'
down_revision = '010_user_summary_suppression'
branch_labels = None
depends_on = None


def upgrade():
    # Add account_type column with default 'end_user'
    # This backfills all existing accounts to 'end_user'
    op.add_column(
        'accounts',
        sa.Column('account_type', sa.String(20), nullable=False, server_default='end_user')
    )
    op.create_index('ix_accounts_account_type', 'accounts', ['account_type'])


def downgrade():
    op.drop_index('ix_accounts_account_type', table_name='accounts')
    op.drop_column('accounts', 'account_type')
