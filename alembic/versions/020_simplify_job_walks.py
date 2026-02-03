"""Add walk_notes and job_walk_status to activities

Revision ID: 020_simplify_job_walks
Revises: 019_segment_cable_len
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

revision = "020_simplify_job_walks"
down_revision = "019_segment_cable_len"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("activities", sa.Column("walk_notes", sa.Text(), nullable=True))
    op.add_column("activities", sa.Column("job_walk_status", sa.String(50), nullable=True))

    # Migrate existing job walks
    op.execute("""
        UPDATE activities
        SET job_walk_status = CASE
            WHEN estimate_completed = true THEN 'complete'
            ELSE 'open'
        END
        WHERE activity_type = 'job_walk'
    """)


def downgrade():
    op.drop_column("activities", "job_walk_status")
    op.drop_column("activities", "walk_notes")
