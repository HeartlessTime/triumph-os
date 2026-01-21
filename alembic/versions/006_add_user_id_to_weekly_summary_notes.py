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


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a foreign key constraint exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    fks = inspector.get_foreign_keys(table_name)
    return any(fk.get("name") == constraint_name for fk in fks)


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name  # "sqlite" or "postgresql"

    # Check if migration has already been applied
    if column_exists("weekly_summary_notes", "user_id"):
        return  # Already migrated

    if dialect == "sqlite":
        # SQLite requires batch mode for ALTER TABLE
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
    else:
        # PostgreSQL: direct ALTER TABLE (no table recreation)
        op.add_column(
            "weekly_summary_notes",
            sa.Column("user_id", sa.Integer(), nullable=True),
        )

        # Drop old index if it exists
        if index_exists("weekly_summary_notes", "ix_weekly_summary_notes_week_section"):
            op.drop_index(
                "ix_weekly_summary_notes_week_section",
                table_name="weekly_summary_notes",
            )

        op.create_index(
            "ix_weekly_summary_notes_week_section_user",
            "weekly_summary_notes",
            ["week_start", "section", "user_id"],
            unique=True,
        )

        op.create_foreign_key(
            "fk_weekly_summary_notes_user_id",
            "weekly_summary_notes",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name  # "sqlite" or "postgresql"

    # Check if migration needs to be reversed
    if not column_exists("weekly_summary_notes", "user_id"):
        return  # Already downgraded

    if dialect == "sqlite":
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
    else:
        # PostgreSQL: direct operations
        if constraint_exists("weekly_summary_notes", "fk_weekly_summary_notes_user_id"):
            op.drop_constraint(
                "fk_weekly_summary_notes_user_id",
                "weekly_summary_notes",
                type_="foreignkey",
            )

        if index_exists("weekly_summary_notes", "ix_weekly_summary_notes_week_section_user"):
            op.drop_index(
                "ix_weekly_summary_notes_week_section_user",
                table_name="weekly_summary_notes",
            )

        op.create_index(
            "ix_weekly_summary_notes_week_section",
            "weekly_summary_notes",
            ["week_start", "section"],
            unique=True,
        )

        op.drop_column("weekly_summary_notes", "user_id")

