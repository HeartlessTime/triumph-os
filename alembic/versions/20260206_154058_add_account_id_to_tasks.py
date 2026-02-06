"""Add account_id to tasks

Revision ID: a1b2c3d4e5f6
Revises: 83c4403c8cb9
Create Date: 2025-02-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "83c4403c8cb9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_tasks_account_id", ["account_id"])
        batch_op.create_foreign_key(
            "fk_tasks_account_id",
            "accounts",
            ["account_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("fk_tasks_account_id", type_="foreignkey")
        batch_op.drop_index("ix_tasks_account_id")
        batch_op.drop_column("account_id")
