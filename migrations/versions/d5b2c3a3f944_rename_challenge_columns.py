"""Rename challenge columns

Revision ID: d5b2c3a3f944
Revises: a970d027ef25
Create Date: 2021-04-25 18:45:33.117263

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5b2c3a3f944'
down_revision = 'a970d027ef25'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('users', 'kings_game_points', 'schosel_points')
    op.alter_column('users', 'oldfashioned_points', 'loser_points')
    op.alter_column('users', 'secret_points', 'comeback_points')


def downgrade():
    op.alter_column('users', 'schosel_points', 'kings_game_points')
    op.alter_column('users', 'loser_points', 'oldfashioned_points')
    op.alter_column('users', 'comeback_points', 'secret_points')
