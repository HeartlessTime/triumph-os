"""
add user_id to weekly_summary_notes

Revision ID: 006_user_id_notes
Revises: 005_task_completed_by
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "006_user_id_notes"
down_revision = "005_task_completed_by"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade():
    # Check if migration has already been applied
    if column_exists("weekly_summary_notes", "user_id"):
        return  # Already migrated

    with op.batch_alter_table("weekly_summary_notes", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), nullable=True)
        )

        # Only drop old index if it exists
        if index_exists("weekly_summary_notes", "ix_weekly_summary_notes_week_section"):
            batch_op.drop_index("ix_weekly_summary_notes_week_section")

        batch_op.create_index(
            "ix_weekly_summary_notes_week_section_user",
            ["week_start", "section", "user_id"],
            unique=True,
        )

        batch_op.create_foreign_key(
            "fk_weekly_summary_notes_user_id",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade():
    # Check if migration needs to be reversed
    if not column_exists("weekly_summary_notes", "user_id"):
        return  # Already downgraded

    with op.batch_alter_table("weekly_summary_notes", recreate="always") as batch_op:
        batch_op.drop_constraint(
            "fk_weekly_summary_notes_user_id",
            type_="foreignkey",
        )

        batch_op.drop_index("ix_weekly_summary_notes_week_section_user")

        batch_op.create_index(
            "ix_weekly_summary_notes_week_section",
            ["week_start", "section"],
            unique=True,
        )

        batch_op.drop_column("user_id")

