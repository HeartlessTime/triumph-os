from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_opportunity_ownership_fields"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "opportunities",
        sa.Column("owner_id", sa.Integer(), nullable=True)
    )

    op.add_column(
        "opportunities",
        sa.Column("assigned_estimator_id", sa.Integer(), nullable=True)
    )

    op.add_column(
        "opportunities",
        sa.Column("hdd_value", sa.Numeric(15, 2), nullable=True)
    )


def downgrade():
    op.drop_column("opportunities", "hdd_value")
    op.drop_column("opportunities", "assigned_estimator_id")
    op.drop_column("opportunities", "owner_id")
