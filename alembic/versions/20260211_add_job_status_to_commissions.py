"""Add job_status to commission_entries

Revision ID: b2c3d4e5f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("commission_entries") as batch_op:
        batch_op.add_column(
            sa.Column("job_status", sa.String(20), nullable=False, server_default="Pending")
        )
        batch_op.create_index("ix_commission_entries_job_status", ["job_status"])


def downgrade():
    with op.batch_alter_table("commission_entries") as batch_op:
        batch_op.drop_index("ix_commission_entries_job_status")
        batch_op.drop_column("job_status")
