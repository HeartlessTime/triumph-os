"""
Add multi-account support for opportunities

Creates opportunity_accounts junction table for many-to-many relationship.
Adds primary_account_id to opportunities table.
Migrates existing account_id data to new structure.

Revision ID: 009_multi_account_opportunities
Revises: 008_add_job_walk_fields
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy import inspect

revision = "009_multi_account_opportunities"
down_revision = "008_add_job_walk_fields"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name  # "sqlite" or "postgresql"

    # 1. Create opportunity_accounts junction table (if not exists)
    if not table_exists("opportunity_accounts"):
        op.create_table(
            "opportunity_accounts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "opportunity_id",
                sa.Integer(),
                sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "account_id",
                sa.Integer(),
                sa.ForeignKey("accounts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                default=datetime.utcnow,
            ),
        )

        op.create_index(
            "ix_opportunity_accounts_opportunity_id",
            "opportunity_accounts",
            ["opportunity_id"],
        )
        op.create_index(
            "ix_opportunity_accounts_account_id",
            "opportunity_accounts",
            ["account_id"],
        )

    # 2. Add primary_account_id column (if not exists)
    if not column_exists("opportunities", "primary_account_id"):
        if dialect == "sqlite":
            # SQLite requires batch mode for ALTER TABLE
            with op.batch_alter_table("opportunities", recreate="always") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "primary_account_id",
                        sa.Integer(),
                        nullable=True,
                    )
                )
                batch_op.create_index(
                    "ix_opportunities_primary_account_id",
                    ["primary_account_id"],
                )
        else:
            # PostgreSQL: direct ALTER TABLE (no table recreation)
            op.add_column(
                "opportunities",
                sa.Column("primary_account_id", sa.Integer(), nullable=True),
            )
            op.create_index(
                "ix_opportunities_primary_account_id",
                "opportunities",
                ["primary_account_id"],
            )

    # 3. Migrate existing data
    rows = conn.execute(
        sa.text(
            "SELECT id, account_id FROM opportunities WHERE account_id IS NOT NULL"
        )
    ).fetchall()

    for opp_id, account_id in rows:
        # Check if junction record already exists
        existing = conn.execute(
            sa.text(
                """
                SELECT 1 FROM opportunity_accounts
                WHERE opportunity_id = :opp_id AND account_id = :acc_id
                """
            ),
            {"opp_id": opp_id, "acc_id": account_id},
        ).fetchone()

        if not existing:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO opportunity_accounts (opportunity_id, account_id, created_at)
                    VALUES (:opp_id, :acc_id, :now)
                    """
                ),
                {"opp_id": opp_id, "acc_id": account_id, "now": datetime.utcnow()},
            )

        conn.execute(
            sa.text(
                """
                UPDATE opportunities
                SET primary_account_id = :acc_id
                WHERE id = :opp_id AND primary_account_id IS NULL
                """
            ),
            {"opp_id": opp_id, "acc_id": account_id},
        )


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name  # "sqlite" or "postgresql"

    # Drop column and index
    if column_exists("opportunities", "primary_account_id"):
        if dialect == "sqlite":
            with op.batch_alter_table("opportunities", recreate="always") as batch_op:
                batch_op.drop_index("ix_opportunities_primary_account_id")
                batch_op.drop_column("primary_account_id")
        else:
            # PostgreSQL: direct operations
            if index_exists("opportunities", "ix_opportunities_primary_account_id"):
                op.drop_index(
                    "ix_opportunities_primary_account_id",
                    table_name="opportunities",
                )
            op.drop_column("opportunities", "primary_account_id")

    # Drop junction table
    if table_exists("opportunity_accounts"):
        if index_exists("opportunity_accounts", "ix_opportunity_accounts_account_id"):
            op.drop_index(
                "ix_opportunity_accounts_account_id",
                table_name="opportunity_accounts",
            )
        if index_exists("opportunity_accounts", "ix_opportunity_accounts_opportunity_id"):
            op.drop_index(
                "ix_opportunity_accounts_opportunity_id",
                table_name="opportunity_accounts",
            )
        op.drop_table("opportunity_accounts")
