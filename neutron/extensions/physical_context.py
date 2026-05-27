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

from neutron_lib.api import extensions as api_extensions
from neutron_lib.plugins import directory
from neutron_lib.services import base as service_base

from neutron.api import extensions
from neutron.api.v2 import base

PLUGIN_TYPE = 'physical-context'

PHYSNET_RESOURCE_NAME = 'physnet_context'
PHYSNET_COLLECTION_NAME = 'physnet_contexts'

SWITCH_RESOURCE_NAME = 'switch_context'
SWITCH_COLLECTION_NAME = 'switch_contexts'

# All fields are read-only; 'validate' specs are placeholders only since
# these resources have no POST/PUT — validators are never invoked on GETs.
_RO_STR = {
    'allow_post': False,
    'allow_put': False,
    'validate': {'type:string': None},
    'is_visible': True,
}

_RO_LIST = {
    'allow_post': False,
    'allow_put': False,
    'validate': {'type:string': None},
    'is_visible': True,
}

PHYSNET_RESOURCE_ATTRIBUTE_MAP = {
    PHYSNET_COLLECTION_NAME: {
        'id': dict(_RO_STR, primary_key=True),
        'physical_network': dict(_RO_STR),
        'networks': dict(_RO_LIST),
    }
}

SWITCH_RESOURCE_ATTRIBUTE_MAP = {
    SWITCH_COLLECTION_NAME: {
        'id': dict(_RO_STR, primary_key=True),
        'physical_network': dict(_RO_STR),
        'networks': dict(_RO_LIST),
    }
}


class _ApiDef:
    """Minimal api_definition to satisfy APIExtensionDescriptor."""
    ALIAS = PLUGIN_TYPE
    NAME = 'Physical Context'
    API_PREFIX = ''
    DESCRIPTION = ('Read-only topology view returning networks, segments, '
                   'ports, and routers for a given physical network or '
                   'switch identifier.')
    UPDATED_TIMESTAMP = '2025-01-01T00:00:00-00:00'
    RESOURCE_ATTRIBUTE_MAP = {}
    SUB_RESOURCE_ATTRIBUTE_MAP = {}
    ACTION_MAP = {}
    ACTION_STATUS = {}
    REQUIRED_EXTENSIONS = []
    OPTIONAL_EXTENSIONS = []
    IS_SHIM_EXTENSION = False
    IS_STANDARD_ATTR_EXTENSION = False


class PhysicalContext(api_extensions.APIExtensionDescriptor):
    """Extension providing read-only physical topology context."""

    api_definition = _ApiDef

    @classmethod
    def get_resources(cls):
        plugin = directory.get_plugin(PLUGIN_TYPE)
        resources = []

        for collection, resource, attr_map in (
            (PHYSNET_COLLECTION_NAME, PHYSNET_RESOURCE_NAME,
             PHYSNET_RESOURCE_ATTRIBUTE_MAP),
            (SWITCH_COLLECTION_NAME, SWITCH_RESOURCE_NAME,
             SWITCH_RESOURCE_ATTRIBUTE_MAP),
        ):
            url_collection = collection.replace('_', '-')
            params = attr_map.get(collection, {})
            controller = base.create_resource(
                url_collection, resource, plugin, params, allow_bulk=False)
            resources.append(
                extensions.ResourceExtension(
                    url_collection, controller, attr_map=params))

        return resources

    @classmethod
    def get_plugin_interface(cls):
        return PhysicalContextPluginBase


class PhysicalContextPluginBase(service_base.ServicePluginBase,
                                metaclass=abc.ABCMeta):
    """Plugin interface for the physical-context extension."""

    @classmethod
    def get_plugin_type(cls):
        return PLUGIN_TYPE

    def get_plugin_description(self):
        return ('Provides read-only topology views by physical network '
                'or switch.')

    @abc.abstractmethod
    def get_physnet_context(self, context, id, fields=None):
        """Return the topology context for a named physical network.

        :param id: physical_network name (e.g. 'physnet1')
        :returns: PhysicalContext dict
        :raises PhysicalNetworkNotFound: if no segments exist for the physnet
        """

    @abc.abstractmethod
    def get_physnet_contexts(self, context, filters=None, fields=None,
                             sorts=None, limit=None, marker=None,
                             page_reverse=False):
        """List endpoint — not implemented in the reference plugin."""

    @abc.abstractmethod
    def get_switch_context(self, context, id, fields=None):
        """Return the topology context for a switch.

        Resolves the switch identifier (switch_id MAC or switch_info hostname)
        from local_link_information to a physical_network, then delegates to
        get_physnet_context.

        :param id: switch_id (MAC) or switch_info (hostname) value from
                   binding:profile local_link_information
        :returns: PhysicalContext dict (same schema as get_physnet_context)
        :raises SwitchNotFound: if no ports reference this switch identifier
        """

    @abc.abstractmethod
    def get_switch_contexts(self, context, filters=None, fields=None,
                            sorts=None, limit=None, marker=None,
                            page_reverse=False):
        """List endpoint — not implemented in the reference plugin."""
