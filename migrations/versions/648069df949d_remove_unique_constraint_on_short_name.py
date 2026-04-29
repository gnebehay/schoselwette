"""Remove unique constraint on short name

Revision ID: 648069df949d
Revises: 2bd8882b3d94
Create Date: 2021-04-11 15:20:33.043777

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '648069df949d'
down_revision = '2bd8882b3d94'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite assigned an auto-generated name to this constraint, so it can't be
    # dropped by name. Recreate the table without it instead.
    op.execute('ALTER TABLE teams RENAME TO teams_old')
    op.create_table('teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('short_name', sa.String(length=3), nullable=False),
        sa.Column('group', sa.String(length=1), nullable=False),
        sa.Column('champion', sa.Boolean(), nullable=False),
        sa.Column('odds', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.execute('INSERT INTO teams SELECT * FROM teams_old')
    op.drop_table('teams_old')


def downgrade():
    with op.batch_alter_table('teams') as batch_op:
        batch_op.create_unique_constraint('uq_teams_short_name', ['short_name'])
