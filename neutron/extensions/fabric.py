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

import abc

from neutron_lib.api.definitions import fabric as apidef
from neutron_lib.api import extensions as api_extensions
from neutron_lib.plugins import constants as plugin_constants
from neutron_lib.plugins import directory
from neutron_lib.services import base as service_base

from neutron.api import extensions
from neutron.api.v2 import base


class Fabric(api_extensions.APIExtensionDescriptor):
    """Extension class supporting VXLAN Fabric resources."""

    api_definition = apidef

    @classmethod
    def get_resources(cls):
        plugin = directory.get_plugin(plugin_constants.FABRIC)
        collection_name = apidef.COLLECTION_NAME.replace('_', '-')
        params = apidef.RESOURCE_ATTRIBUTE_MAP.get(apidef.COLLECTION_NAME,
                                                   dict())
        controller = base.create_resource(collection_name,
                                          apidef.RESOURCE_NAME,
                                          plugin, params, allow_bulk=True,
                                          allow_pagination=True,
                                          allow_sorting=True)
        ex = extensions.ResourceExtension(collection_name, controller,
                                          attr_map=params)
        return [ex]

    @classmethod
    def get_plugin_interface(cls):
        return FabricPluginBase


class FabricPluginBase(service_base.ServicePluginBase,
                       metaclass=abc.ABCMeta):
    """REST API to manage VXLAN fabrics."""

    @classmethod
    def get_plugin_type(cls):
        return plugin_constants.FABRIC

    def get_plugin_description(self):
        return "Provides management of VXLAN fabrics"

    @abc.abstractmethod
    def create_fabric(self, context, fabric):
        pass

    @abc.abstractmethod
    def update_fabric(self, context, id, fabric):
        pass

    @abc.abstractmethod
    def delete_fabric(self, context, id):
        pass

    @abc.abstractmethod
    def get_fabrics(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False):
        pass

    @abc.abstractmethod
    def get_fabric(self, context, id, fields=None):
        pass
