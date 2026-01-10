"""add weekly summary notes table

Revision ID: 003_weekly_summary_notes
Revises: 002_contact_followup
Create Date: 2026-01-09
"""
from alembic import op
import sqlalchemy as sa

revision = '003_weekly_summary_notes'
down_revision = '002_contact_followup'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'weekly_summary_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('section', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_weekly_summary_notes_week_start', 'weekly_summary_notes', ['week_start'])
    op.create_index('ix_weekly_summary_notes_section', 'weekly_summary_notes', ['section'])
    op.create_index('ix_weekly_summary_notes_week_section', 'weekly_summary_notes', ['week_start', 'section'])


def downgrade():
    op.drop_index('ix_weekly_summary_notes_week_section', 'weekly_summary_notes')
    op.drop_index('ix_weekly_summary_notes_section', 'weekly_summary_notes')
    op.drop_index('ix_weekly_summary_notes_week_start', 'weekly_summary_notes')
    op.drop_table('weekly_summary_notes')
