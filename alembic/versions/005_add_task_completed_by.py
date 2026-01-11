"""add completed_by_id to tasks

Revision ID: 005_task_completed_by
Revises: 004_stalled_reason
Create Date: 2026-01-10
"""
from alembic import op
import sqlalchemy as sa

revision = '005_task_completed_by'
down_revision = '004_stalled_reason'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tasks',
        sa.Column('completed_by_id', sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column('tasks', 'completed_by_id')
