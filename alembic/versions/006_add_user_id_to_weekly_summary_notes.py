"""add user_id to weekly_summary_notes

Revision ID: 006_user_id_notes
Revises: 005_task_completed_by
Create Date: 2026-01-10

Adds user_id column to weekly_summary_notes to separate:
- Team notes (user_id = NULL)
- Personal notes (user_id = user's id)
"""
from alembic import op
import sqlalchemy as sa

revision = '006_user_id_notes'
down_revision = '005_task_completed_by'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'weekly_summary_notes',
        sa.Column('user_id', sa.Integer(), nullable=True)
    )
    op.create_index(
        'ix_weekly_summary_notes_user_id',
        'weekly_summary_notes',
        ['user_id']
    )
    op.create_foreign_key(
        'fk_weekly_summary_notes_user_id',
        'weekly_summary_notes',
        'users',
        ['user_id'],
        ['id']
    )
    # Drop old composite index and create new one with user_id
    op.drop_index('ix_weekly_summary_notes_week_section', table_name='weekly_summary_notes')
    op.create_index(
        'ix_weekly_summary_notes_week_section_user',
        'weekly_summary_notes',
        ['week_start', 'section', 'user_id']
    )


def downgrade():
    op.drop_index('ix_weekly_summary_notes_week_section_user', table_name='weekly_summary_notes')
    op.create_index(
        'ix_weekly_summary_notes_week_section',
        'weekly_summary_notes',
        ['week_start', 'section']
    )
    op.drop_constraint('fk_weekly_summary_notes_user_id', 'weekly_summary_notes', type_='foreignkey')
    op.drop_index('ix_weekly_summary_notes_user_id', table_name='weekly_summary_notes')
    op.drop_column('weekly_summary_notes', 'user_id')
