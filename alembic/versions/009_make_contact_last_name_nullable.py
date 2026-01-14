"""make contact last_name nullable

Revision ID: 009_last_name_nullable
Revises: 008_add_job_walk_fields
Create Date: 2026-01-14
"""
from alembic import op
import sqlalchemy as sa

revision = '009_last_name_nullable'
down_revision = '008_add_job_walk_fields'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite doesn't support ALTER COLUMN, so we use batch mode
    # Make last_name nullable - contacts should only require first_name
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.alter_column('last_name',
            existing_type=sa.String(100),
            nullable=True
        )


def downgrade():
    # Revert to NOT NULL (will fail if any NULL values exist)
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.alter_column('last_name',
            existing_type=sa.String(100),
            nullable=False
        )
