"""add bet metrics table

Revision ID: a2d3f4b5c6e7
Revises: 99a489f08eeb
Create Date: 2026-05-15 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a2d3f4b5c6e7"
down_revision = "99a489f08eeb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bet_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("bet_metrics")
