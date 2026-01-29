"""Add activity_attendees junction table for multi-contact meetings

Revision ID: 014_add_activity_attendees
Revises: 013_add_account_is_hot
Create Date: 2026-01-29
"""
from alembic import op
import sqlalchemy as sa

revision = '014_add_activity_attendees'
down_revision = '013_add_account_is_hot'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'activity_attendees',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('activity_id', sa.Integer(), sa.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contact_id', sa.Integer(), sa.ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_activity_attendees_activity_id', 'activity_attendees', ['activity_id'])
    op.create_index('ix_activity_attendees_contact_id', 'activity_attendees', ['contact_id'])


def downgrade():
    op.drop_index('ix_activity_attendees_contact_id', table_name='activity_attendees')
    op.drop_index('ix_activity_attendees_activity_id', table_name='activity_attendees')
    op.drop_table('activity_attendees')
