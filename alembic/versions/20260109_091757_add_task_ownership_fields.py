"""add task ownership fields

Revision ID: 6040c5e8b799
Revises: 4d22e734184d
Create Date: 2026-01-09 09:17:57.426035
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6040c5e8b799"
down_revision: Union[str, None] = "4d22e734184d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("assigned_to_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("created_by_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "created_by_id")
    op.drop_column("tasks", "assigned_to_id")
