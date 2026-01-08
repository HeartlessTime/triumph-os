"""add opportunity fields for bid instructions and lv value

Revision ID: 002_add_opportunity_fields
Revises: 001_initial
Create Date: 2026-01-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_opportunity_fields'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('opportunities', sa.Column('bid_type', sa.String(length=50), nullable=True))
    op.add_column('opportunities', sa.Column('submission_method', sa.String(length=50), nullable=True))
    op.add_column('opportunities', sa.Column('bid_time', sa.Time(), nullable=True))
    op.add_column('opportunities', sa.Column('bid_form_required', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('opportunities', sa.Column('bond_required', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('opportunities', sa.Column('prevailing_wage', sa.String(length=20), nullable=True))
    op.add_column('opportunities', sa.Column('known_risks', sa.Text(), nullable=True))
    op.add_column('opportunities', sa.Column('project_type', sa.String(length=50), nullable=True))
    op.add_column('opportunities', sa.Column('rebid', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('opportunities', sa.Column('rebid_changes', sa.Text(), nullable=True))
    op.add_column('opportunities', sa.Column('lv_value', sa.Numeric(15,2), nullable=True))


def downgrade():
    op.drop_column('opportunities', 'lv_value')
    op.drop_column('opportunities', 'rebid_changes')
    op.drop_column('opportunities', 'rebid')
    op.drop_column('opportunities', 'project_type')
    op.drop_column('opportunities', 'known_risks')
    op.drop_column('opportunities', 'prevailing_wage')
    op.drop_column('opportunities', 'bond_required')
    op.drop_column('opportunities', 'bid_form_required')
    op.drop_column('opportunities', 'bid_time')
    op.drop_column('opportunities', 'submission_method')
    op.drop_column('opportunities', 'bid_type')
