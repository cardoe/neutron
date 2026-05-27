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

from neutron_lib.api.definitions import fabric as apidef
from neutron_lib.api.definitions import network as net_def
from neutron_lib.db import api as db_api
from neutron_lib.db import resource_extend
from neutron_lib import exceptions as lib_exc
from neutron_lib.plugins import constants as plugin_constants
from oslo_log import log

from neutron.extensions import fabric as ext_fabric
from neutron.objects import base as base_obj
from neutron.objects import fabric as obj_fabric

LOG = log.getLogger(__name__)


@resource_extend.has_resource_extenders
class FabricPlugin(ext_fabric.FabricPluginBase):
    """Implements the Neutron Fabric service plugin."""

    supported_extension_aliases = [apidef.ALIAS]

    __native_pagination_support = True
    __native_sorting_support = True

    def _get_fabric(self, context, id):
        obj = obj_fabric.Fabric.get_object(context, id=id)
        if obj is None:
            raise lib_exc.ObjectNotFound(id=id)
        return obj

    @staticmethod
    @resource_extend.extends([net_def.COLLECTION_NAME])
    def _extend_network_dict_fabric(network_res, network_db):
        binding = network_db.fabric_binding
        network_res[apidef.FABRIC_ID] = (
            binding.fabric_id if binding else None)
        return network_res

    def create_fabric(self, context, fabric):
        fabric_data = fabric['fabric']
        with db_api.CONTEXT_WRITER.using(context):
            fabric_obj = obj_fabric.Fabric(
                context,
                name=fabric_data.get('name', ''),
                physical_network=fabric_data['physical_network'],
                shared=fabric_data.get('shared', False),
                project_id=(fabric_data['project_id']
                            if not fabric_data.get('shared') else None),
            )
            fabric_obj.create()
        return fabric_obj.to_dict()

    def update_fabric(self, context, id, fabric):
        fabric_data = fabric['fabric']
        with db_api.CONTEXT_WRITER.using(context):
            fabric_obj = self._get_fabric(context, id)
            fabric_obj.update_fields(fabric_data)
            fabric_obj.update()
        return fabric_obj.to_dict()

    def delete_fabric(self, context, id):
        with db_api.CONTEXT_WRITER.using(context):
            fabric_obj = self._get_fabric(context, id)
            fabric_obj.delete()

    def get_fabrics(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False):
        pager = base_obj.Pager(sorts, limit, page_reverse, marker)
        filters = filters or {}
        return [f.to_dict(fields=fields)
                for f in obj_fabric.Fabric.get_objects(
                    context, _pager=pager, **filters)]

    def get_fabric(self, context, id, fields=None):
        return self._get_fabric(context, id).to_dict(fields=fields)

    def get_plugin_description(self):
        return "Provides management of VXLAN fabrics"

    @classmethod
    def get_plugin_type(cls):
        return plugin_constants.FABRIC
