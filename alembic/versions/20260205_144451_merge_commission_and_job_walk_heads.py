"""merge commission and job walk heads

Revision ID: 5c9cc5e66aa7
Revises: 017_add_commission_entries, 022_add_job_walk_labor_fields
Create Date: 2026-02-05 14:44:51.970872

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c9cc5e66aa7'
down_revision: Union[str, None] = ('017_add_commission_entries', '022_add_job_walk_labor_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
