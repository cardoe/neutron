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

from neutron_lib.db import constants as db_const
from neutron_lib.db import model_base
from neutron_lib.db import standard_attr
import sqlalchemy as sa
from sqlalchemy import orm

from neutron.db import models_v2


class Fabric(standard_attr.HasStandardAttributes, model_base.BASEV2,
             model_base.HasId, model_base.HasProject):
    """Represents a VXLAN fabric."""

    __tablename__ = 'fabrics'

    name = sa.Column(sa.String(db_const.NAME_FIELD_SIZE), nullable=True)
    physical_network = sa.Column(sa.String(64), nullable=False)
    shared = sa.Column(sa.Boolean, default=False, nullable=False)

    api_collections = ['fabrics']
    collection_resource_map = {'fabrics': 'fabric'}


class NetworkFabric(model_base.BASEV2):
    """Associates a network with a fabric."""

    __tablename__ = 'network_fabrics'

    network_id = sa.Column(sa.String(db_const.UUID_FIELD_SIZE),
                           sa.ForeignKey('networks.id', ondelete='CASCADE'),
                           primary_key=True, nullable=False)
    fabric_id = sa.Column(sa.String(db_const.UUID_FIELD_SIZE),
                          sa.ForeignKey('fabrics.id', ondelete='SET NULL'),
                          nullable=True)

    network = orm.relationship(
        models_v2.Network, load_on_pending=True,
        backref=orm.backref('fabric_binding', lazy='joined',
                            uselist=False, cascade='delete'))
    revises_on_change = ('network',)
