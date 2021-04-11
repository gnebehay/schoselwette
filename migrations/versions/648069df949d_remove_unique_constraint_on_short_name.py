"""Remove unique constraint on short name

Revision ID: 648069df949d
Revises: 2bd8882b3d94
Create Date: 2021-04-11 15:20:33.043777

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '648069df949d'
down_revision = '2bd8882b3d94'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('short_name', 'teams', 'unique')


def downgrade():
    op.create_unique_constraint("short_name", "teams", ["short_name"])
