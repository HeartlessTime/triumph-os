"""make probability nullable

Revision ID: 004_make_probability_nullable
Revises: 003_modify_opportunity_values
Create Date: 2026-01-07 17:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_make_probability_nullable'
down_revision = '003_modify_opportunity_values'
branch_labels = None
depends_on = None


def upgrade():
    # Make probability column nullable (if DB enforces NOT NULL)
    with op.batch_alter_table('opportunities') as batch_op:
        try:
            batch_op.alter_column('probability', existing_type=sa.Integer(), nullable=True)
        except Exception:
            pass


def downgrade():
    with op.batch_alter_table('opportunities') as batch_op:
        try:
            batch_op.alter_column('probability', existing_type=sa.Integer(), nullable=False)
        except Exception:
            pass
