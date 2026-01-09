"""add contact followup fields

Revision ID: 002_contact_followup
Revises: 001_initial
Create Date: 2026-01-09
"""
from alembic import op
import sqlalchemy as sa

revision = '002_contact_followup'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add last_contacted and next_followup columns to contacts table
    op.add_column('contacts', sa.Column('last_contacted', sa.Date(), nullable=True))
    op.add_column('contacts', sa.Column('next_followup', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('contacts', 'next_followup')
    op.drop_column('contacts', 'last_contacted')
