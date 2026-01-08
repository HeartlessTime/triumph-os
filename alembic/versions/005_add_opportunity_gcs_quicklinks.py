"""add gcs, related contacts, quick_links and end_user_account to opportunities

Revision ID: 005_add_opportunity_gcs_quicklinks
Revises: 004_make_probability_nullable
Create Date: 2026-01-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_add_opportunity_gcs_quicklinks'
down_revision = '004_make_probability_nullable'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('opportunities', sa.Column('gcs', sa.JSON(), nullable=True))
    op.add_column('opportunities', sa.Column('related_contact_ids', sa.JSON(), nullable=True))
    op.add_column('opportunities', sa.Column('quick_links', sa.JSON(), nullable=True))
    op.add_column('opportunities', sa.Column('end_user_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_opportunities_end_user_account_id_accounts',
        'opportunities', 'accounts', ['end_user_account_id'], ['id']
    )


def downgrade():
    op.drop_constraint('fk_opportunities_end_user_account_id_accounts', 'opportunities', type_='foreignkey')
    op.drop_column('opportunities', 'end_user_account_id')
    op.drop_column('opportunities', 'quick_links')
    op.drop_column('opportunities', 'related_contact_ids')
    op.drop_column('opportunities', 'gcs')
