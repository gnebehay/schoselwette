"""add sync metrics table

Revision ID: b3c4d5e6f7a1
Revises: a2d3f4b5c6e7
Create Date: 2026-06-14 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a1"
down_revision = "a2d3f4b5c6e7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sync_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("sync_metrics")
