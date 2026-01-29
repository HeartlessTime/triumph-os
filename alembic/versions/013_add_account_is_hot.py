"""Add is_hot boolean to accounts

Revision ID: 013_add_account_is_hot
Revises: 012_add_tracking_fields
Create Date: 2026-01-29
"""
from alembic import op
import sqlalchemy as sa

revision = '013_add_account_is_hot'
down_revision = '012_add_tracking_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'accounts',
        sa.Column('is_hot', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    op.create_index('ix_accounts_is_hot', 'accounts', ['is_hot'])


def downgrade():
    op.drop_index('ix_accounts_is_hot', table_name='accounts')
    op.drop_column('accounts', 'is_hot')
