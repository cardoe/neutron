# Copyright (c) 2025 Rackspace Technology.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from alembic import op
import sqlalchemy as sa

from neutron_lib.db import constants as db_const

"""Add fabrics table and network_fabrics binding

Revision ID: d63f8b446cc7
Revises: 5881373af7f5
Create Date: 2025-05-15 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = 'd63f8b446cc7'
down_revision = '5881373af7f5'


def upgrade():
    op.create_table(
        'fabrics',
        sa.Column('id', sa.String(length=db_const.UUID_FIELD_SIZE),
                  nullable=False, primary_key=True),
        sa.Column('standard_attr_id', sa.BigInteger(), nullable=False),
        sa.Column('project_id',
                  sa.String(length=db_const.PROJECT_ID_FIELD_SIZE),
                  nullable=True),
        sa.Column('name', sa.String(length=db_const.NAME_FIELD_SIZE),
                  nullable=True),
        sa.Column('physical_network', sa.String(length=64), nullable=False),
        sa.Column('shared', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.ForeignKeyConstraint(['standard_attr_id'],
                                ['standardattributes.id'],
                                ondelete='CASCADE'),
        sa.UniqueConstraint('standard_attr_id'),
    )

    op.create_table(
        'network_fabrics',
        sa.Column('network_id', sa.String(length=db_const.UUID_FIELD_SIZE),
                  sa.ForeignKey('networks.id', ondelete='CASCADE'),
                  nullable=False, primary_key=True),
        sa.Column('fabric_id', sa.String(length=db_const.UUID_FIELD_SIZE),
                  sa.ForeignKey('fabrics.id', ondelete='SET NULL'),
                  nullable=True),
    )
