"""Add daily_briefings table

Revision ID: 83c4403c8cb9
Revises: 5c9cc5e66aa7
Create Date: 2026-02-06 08:53:38.614882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '83c4403c8cb9'
down_revision: Union[str, None] = '5c9cc5e66aa7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('daily_briefings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('summary_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_daily_briefings_summary_date'), 'daily_briefings', ['summary_date'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_daily_briefings_summary_date'), table_name='daily_briefings')
    op.drop_table('daily_briefings')
