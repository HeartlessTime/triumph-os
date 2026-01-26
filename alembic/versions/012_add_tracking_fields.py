"""Add awaiting_response to accounts and has_responded to contacts

Revision ID: 012_add_tracking_fields
Revises: 044e480b5760
Create Date: 2026-01-26
"""
from alembic import op
import sqlalchemy as sa

revision = '012_add_tracking_fields'
down_revision = '044e480b5760'
branch_labels = None
depends_on = None


def upgrade():
    # Add awaiting_response to accounts table
    op.add_column(
        'accounts',
        sa.Column('awaiting_response', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    op.create_index('ix_accounts_awaiting_response', 'accounts', ['awaiting_response'])

    # Add has_responded to contacts table
    op.add_column(
        'contacts',
        sa.Column('has_responded', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade():
    op.drop_column('contacts', 'has_responded')
    op.drop_index('ix_accounts_awaiting_response', table_name='accounts')
    op.drop_column('accounts', 'awaiting_response')
