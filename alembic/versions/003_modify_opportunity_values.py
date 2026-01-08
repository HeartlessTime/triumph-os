"""modify opportunity values: remove overall value, remove rebid_changes, add hdd_value

Revision ID: 003_modify_opportunity_values
Revises: 002_add_opportunity_fields
Create Date: 2026-01-07 16:40:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_modify_opportunity_values'
down_revision = '002_add_opportunity_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add hdd_value
    op.add_column('opportunities', sa.Column('hdd_value', sa.Numeric(15, 2), nullable=True))
    # Drop overall GC project value if exists
    with op.batch_alter_table('opportunities') as batch_op:
        try:
            batch_op.drop_column('value')
        except Exception:
            # column may not exist, ignore
            pass
        try:
            batch_op.drop_column('rebid_changes')
        except Exception:
            pass


def downgrade():
    # Recreate dropped columns
    with op.batch_alter_table('opportunities') as batch_op:
        batch_op.add_column(sa.Column('value', sa.Numeric(15, 2), nullable=True))
        batch_op.add_column(sa.Column('rebid_changes', sa.Text(), nullable=True))
    # Drop hdd_value
    with op.batch_alter_table('opportunities') as batch_op:
        try:
            batch_op.drop_column('hdd_value')
        except Exception:
            pass
