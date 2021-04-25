"""Add field for api data

Revision ID: a970d027ef25
Revises: 27613b54bcac
Create Date: 2021-04-25 09:47:34.886161

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a970d027ef25'
down_revision = '27613b54bcac'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('matches', sa.Column('api_data', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('matches', 'api_data')