"""empty message

Revision ID: be7c390861ab
Revises: 009_multi_account_opportunities
Create Date: 2026-01-20 16:14:59.344700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be7c390861ab'
down_revision: Union[str, None] = '009_multi_account_opportunities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
