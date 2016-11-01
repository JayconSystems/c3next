"""Initial Schema

Revision ID: 4b58d94990c3
Revises: 
Create Date: 2016-11-01 10:21:59.167841

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4b58d94990c3'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('beacon_groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('password', sa.String(), nullable=False),
    sa.Column('first_name', sa.String(), nullable=False),
    sa.Column('last_name', sa.String(), nullable=False),
    sa.Column('last_login_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('zones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('listeners',
    sa.Column('id', sa.Binary(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('zone_id', sa.Integer(), nullable=True),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('beacons',
    sa.Column('id', sa.Binary(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=True),
    sa.Column('listener_id', sa.Binary(), nullable=True),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    sa.Column('key', sa.Binary(), nullable=False),
    sa.Column('dk', sa.BigInteger(), nullable=False),
    sa.Column('clock', sa.BigInteger(), nullable=False),
    sa.Column('clock_origin', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['beacon_groups.id'], ),
    sa.ForeignKeyConstraint(['listener_id'], ['listeners.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('beacon_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('beacon_id', sa.Binary(), nullable=True),
    sa.Column('listener_id', sa.Binary(), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['beacon_id'], ['beacons.id'], ),
    sa.ForeignKeyConstraint(['listener_id'], ['listeners.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('beacon_logs')
    op.drop_table('beacons')
    op.drop_table('listeners')
    op.drop_table('zones')
    op.drop_table('users')
    op.drop_table('beacon_groups')
    ### end Alembic commands ###
