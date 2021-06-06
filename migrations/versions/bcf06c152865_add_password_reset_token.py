"""Add password reset token

Revision ID: bcf06c152865
Revises: d5b2c3a3f944
Create Date: 2021-06-06 09:24:15.998064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bcf06c152865'
down_revision = 'd5b2c3a3f944'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('reset_token', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'reset_token')
    # ### end Alembic commands ###
