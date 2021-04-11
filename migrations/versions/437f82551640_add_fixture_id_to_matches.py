"""Add fixture_id to matches

Revision ID: 437f82551640
Revises: 648069df949d
Create Date: 2021-04-11 15:49:25.578580

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '437f82551640'
down_revision = '648069df949d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('matches', sa.Column('fixture_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('matches', 'fixture_id')
