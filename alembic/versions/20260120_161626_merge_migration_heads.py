"""merge migration heads

Revision ID: 044e480b5760
Revises: 011_add_account_type, be7c390861ab
Create Date: 2026-01-20 16:16:26.828963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '044e480b5760'
down_revision: Union[str, None] = ('011_add_account_type', 'be7c390861ab')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
