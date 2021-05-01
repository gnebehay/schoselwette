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
    op.alter_column('users', 'kings_game_points', new_column_name='schosel_points', existing_type=sa.Float, existing_nullable=False)
    op.alter_column('users', 'oldfashioned_points', new_column_name='loser_points', existing_type=sa.Float, existing_nullable=False)
    op.alter_column('users', 'secret_points', new_column_name='comeback_points', existing_type=sa.Float, existing_nullable=False)


def downgrade():
    op.alter_column('users', 'schosel_points', new_column_name='kings_game_points', existing_type=sa.Float, existing_nullable=False)
    op.alter_column('users', 'loser_points', new_column_name='oldfashioned_points', existing_type=sa.Float, existing_nullable=False)
    op.alter_column('users', 'comeback_points', new_column_name='secret_points', existing_type=sa.Float, existing_nullable=False)
