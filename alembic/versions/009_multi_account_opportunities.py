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

revision = "009_multi_account_opportunities"
down_revision = "008_add_job_walk_fields"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create opportunity_accounts junction table
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

    # 2. Add primary_account_id column (NO FK — SQLite batch-safe)
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

    # 3. Migrate existing data
    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            "SELECT id, account_id FROM opportunities WHERE account_id IS NOT NULL"
        )
    ).fetchall()

    for opp_id, account_id in rows:
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
                WHERE id = :opp_id
                """
            ),
            {"opp_id": opp_id, "acc_id": account_id},
        )


def downgrade():
    with op.batch_alter_table("opportunities", recreate="always") as batch_op:
        batch_op.drop_index("ix_opportunities_primary_account_id")
        batch_op.drop_column("primary_account_id")

    op.drop_index(
        "ix_opportunity_accounts_account_id",
        table_name="opportunity_accounts",
    )
    op.drop_index(
        "ix_opportunity_accounts_opportunity_id",
        table_name="opportunity_accounts",
    )
    op.drop_table("opportunity_accounts")
