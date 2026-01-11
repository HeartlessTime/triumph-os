"""
make activity.opportunity_id nullable

Revision ID: 007_activity_opp_nullable
Revises: 006_user_id_notes
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa

revision = "007_activity_opp_nullable"
down_revision = "006_user_id_notes"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite requires batch mode with full table recreation to change column nullability
    # We must explicitly define the schema for proper recreation
    with op.batch_alter_table(
        "activities",
        recreate="always",
        table_args=(
            sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        ),
    ) as batch_op:
        batch_op.alter_column(
            "opportunity_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade():
    # Note: This will fail if there are any NULL opportunity_id values
    with op.batch_alter_table(
        "activities",
        recreate="always",
        table_args=(
            sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        ),
    ) as batch_op:
        batch_op.alter_column(
            "opportunity_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
