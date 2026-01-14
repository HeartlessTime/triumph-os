"""add user_summary_suppressions table

Revision ID: 010_user_summary_suppression
Revises: 009_last_name_nullable
Create Date: 2026-01-14
"""
from alembic import op
import sqlalchemy as sa

revision = '010_user_summary_suppression'
down_revision = '009_last_name_nullable'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_summary_suppressions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id'), nullable=False, index=True),
        sa.Column('suppressed_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'opportunity_id', name='uq_user_opportunity_suppression')
    )


def downgrade():
    op.drop_table('user_summary_suppressions')
