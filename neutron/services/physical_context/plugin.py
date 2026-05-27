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

import collections

from neutron_lib import constants as lib_const
from neutron_lib.db import api as db_api
from neutron_lib import exceptions as lib_exc
from oslo_log import log
from oslo_serialization import jsonutils
import webob.exc

from neutron.db.models import l3 as l3_models
from neutron.db.models import segment as segment_models
from neutron.db import models_v2
from neutron.extensions import physical_context as ext_pc
from neutron.plugins.ml2 import models as ml2_models

LOG = log.getLogger(__name__)


class PhysicalNetworkNotFound(lib_exc.NotFound):
    message = "Physical network %(physical_network)s not found."


class SwitchNotFound(lib_exc.NotFound):
    message = "No ports found with switch identifier '%(switch)s'."


class PhysicalContextPlugin(ext_pc.PhysicalContextPluginBase):
    """Read-only physical topology context queries.

    Endpoints
    ---------
    GET /v2.0/physnet-contexts/{physical_network}
        Returns all networks whose segments include the named physical_network,
        along with the ports bound to those segments and the routers attached
        via network:router_interface ports.

    GET /v2.0/switch-contexts/{switch_identifier}
        Resolves the switch identifier (switch_id MAC or switch_info hostname)
        from local_link_information in ml2_port_bindings.profile to a
        physical_network, then returns the same context as the physnet endpoint.
        Matches against both switch_id and switch_info fields so callers need
        not know which format the identifier is stored in.
    """

    supported_extension_aliases = [ext_pc.PLUGIN_TYPE]

    # ------------------------------------------------------------------ #
    # Internal query helpers                                               #
    # ------------------------------------------------------------------ #

    def _query_physnet_context(self, context, physical_network):
        with db_api.CONTEXT_READER.using(context):
            session = context.session

            # Segments that belong to this physical_network
            physnet_segments = (
                session.query(segment_models.NetworkSegment)
                .filter_by(physical_network=physical_network)
                .all()
            )
            if not physnet_segments:
                raise PhysicalNetworkNotFound(
                    physical_network=physical_network)

            segment_ids = [s.id for s in physnet_segments]
            network_ids = list({s.network_id for s in physnet_segments})

            # Networks
            networks = (
                session.query(models_v2.Network)
                .filter(models_v2.Network.id.in_(network_ids))
                .all()
            )

            # All segments for those networks (full context, not just the
            # physnet segments — callers need the complete picture)
            all_segments = (
                session.query(segment_models.NetworkSegment)
                .filter(
                    segment_models.NetworkSegment.network_id.in_(network_ids))
                .all()
            )

            # Port IDs that have a binding level mapped to one of our segments.
            # Using ml2_port_binding_levels is the correct join path for
            # multi-segment networks: a port can be on a network that spans
            # multiple physnets, but binding_levels pins it to a specific one.
            bound_port_ids_sq = (
                session.query(ml2_models.PortBindingLevel.port_id)
                .filter(
                    ml2_models.PortBindingLevel.segment_id.in_(segment_ids))
                .distinct()
                .subquery()
            )

            # Active port bindings for those ports.
            # Port.fixed_ips is lazy='selectin' and loads automatically.
            ports_with_bindings = (
                session.query(models_v2.Port, ml2_models.PortBinding)
                .join(ml2_models.PortBinding,
                      models_v2.Port.id == ml2_models.PortBinding.port_id)
                .filter(
                    models_v2.Port.id.in_(bound_port_ids_sq),
                    ml2_models.PortBinding.status == lib_const.ACTIVE,
                )
                .all()
            )

            # Routers attached via network:router_interface ports on these
            # networks.  Gateway ports (network:router_gateway) are excluded
            # per design — they represent the router's uplink, not its
            # attachment to the physnet segment.
            router_rows = (
                session.query(
                    l3_models.Router,
                    l3_models.RouterPort,
                    models_v2.Port.network_id.label('network_id'),
                )
                .join(l3_models.RouterPort,
                      l3_models.Router.id == l3_models.RouterPort.router_id)
                .join(models_v2.Port,
                      l3_models.RouterPort.port_id == models_v2.Port.id)
                .filter(
                    models_v2.Port.network_id.in_(network_ids),
                    l3_models.RouterPort.port_type ==
                    lib_const.DEVICE_OWNER_ROUTER_INTF,
                )
                .all()
            )

            return self._assemble_context(
                physical_network, networks, all_segments,
                ports_with_bindings, router_rows)

    def _assemble_context(self, physical_network, networks, segments,
                          ports_with_bindings, router_rows):
        segs_by_net = collections.defaultdict(list)
        for seg in segments:
            segs_by_net[seg.network_id].append({
                'id': seg.id,
                'name': seg.name,
                'network_type': seg.network_type,
                'physical_network': seg.physical_network,
                'segmentation_id': seg.segmentation_id,
            })

        ports_by_net = collections.defaultdict(list)
        for port, binding in ports_with_bindings:
            try:
                profile = (jsonutils.loads(binding.profile)
                           if binding.profile else {})
            except ValueError:
                profile = {}
            ports_by_net[port.network_id].append({
                'id': port.id,
                'name': port.name,
                'mac_address': port.mac_address,
                'status': port.status,
                'device_owner': port.device_owner,
                'device_id': port.device_id,
                'fixed_ips': [
                    {'ip_address': ip.ip_address, 'subnet_id': ip.subnet_id}
                    for ip in port.fixed_ips
                ],
                'binding_host_id': binding.host,
                'binding_vnic_type': binding.vnic_type,
                'binding_vif_type': binding.vif_type,
                'local_link_information': profile.get(
                    'local_link_information', []),
            })

        routers_by_net = collections.defaultdict(list)
        seen = collections.defaultdict(set)
        for router, rport, network_id in router_rows:
            if router.id not in seen[network_id]:
                seen[network_id].add(router.id)
                routers_by_net[network_id].append({
                    'id': router.id,
                    'name': router.name,
                    'status': router.status,
                    'admin_state_up': router.admin_state_up,
                    'project_id': router.project_id,
                    'interface_port_id': rport.port_id,
                })

        return {
            'id': physical_network,
            'physical_network': physical_network,
            'networks': [
                {
                    'id': net.id,
                    'name': net.name,
                    'status': net.status,
                    'admin_state_up': net.admin_state_up,
                    'project_id': net.project_id,
                    'segments': segs_by_net.get(net.id, []),
                    'ports': ports_by_net.get(net.id, []),
                    'routers': routers_by_net.get(net.id, []),
                }
                for net in networks
            ],
        }

    def _resolve_switch_to_physnet(self, context, switch_identifier):
        """Map a switch_id (MAC) or switch_info (hostname) to a physical_network.

        Strategy:
        1. Coarse SQL LIKE filter on binding.profile to avoid a full table scan.
        2. Exact JSON match in Python against local_link_information[].switch_id
           and local_link_information[].switch_info.
        3. Resolve physical_network via ml2_port_binding_levels → networksegments.
           Falls back to a direct network segment lookup for ports that have
           local_link_information recorded but no binding levels yet (e.g. an
           unbound baremetal port).
        """
        with db_api.CONTEXT_READER.using(context):
            session = context.session

            # Coarse filter: only load bindings whose profile JSON blob
            # contains the identifier string anywhere.
            bindings = (
                session.query(ml2_models.PortBinding)
                .filter(
                    ml2_models.PortBinding.profile.contains(switch_identifier))
                .all()
            )

            matching_port_ids = []
            for binding in bindings:
                try:
                    profile = (jsonutils.loads(binding.profile)
                               if binding.profile else {})
                except ValueError:
                    continue
                for link in profile.get('local_link_information', []):
                    if (link.get('switch_id') == switch_identifier or
                            link.get('switch_info') == switch_identifier):
                        matching_port_ids.append(binding.port_id)
                        break

            if not matching_port_ids:
                raise SwitchNotFound(switch=switch_identifier)

            # Resolve via binding levels (preferred: accounts for
            # multi-segment networks where a port is bound to a specific one)
            physnets = (
                session.query(
                    segment_models.NetworkSegment.physical_network)
                .join(
                    ml2_models.PortBindingLevel,
                    segment_models.NetworkSegment.id ==
                    ml2_models.PortBindingLevel.segment_id)
                .filter(
                    ml2_models.PortBindingLevel.port_id.in_(
                        matching_port_ids),
                    segment_models.NetworkSegment.physical_network.isnot(
                        None))
                .distinct()
                .all()
            )

            if not physnets:
                # Fallback for ports without binding levels: derive physnet
                # from the network's segments directly.  Restricted to flat
                # and vlan types because those are the only ones that map
                # switch connections to a physical_network.
                port_network_ids_sq = (
                    session.query(models_v2.Port.network_id)
                    .filter(models_v2.Port.id.in_(matching_port_ids))
                    .distinct()
                    .subquery()
                )
                physnets = (
                    session.query(
                        segment_models.NetworkSegment.physical_network)
                    .filter(
                        segment_models.NetworkSegment.network_id.in_(
                            port_network_ids_sq),
                        segment_models.NetworkSegment.physical_network.isnot(
                            None),
                        segment_models.NetworkSegment.network_type.in_(
                            [lib_const.TYPE_FLAT, lib_const.TYPE_VLAN]),
                    )
                    .distinct()
                    .all()
                )

            if not physnets:
                raise SwitchNotFound(switch=switch_identifier)

            if len(physnets) > 1:
                LOG.warning(
                    'Switch %s maps to multiple physical networks %s; '
                    'using first result.',
                    switch_identifier, [p[0] for p in physnets])

            return physnets[0][0]

    # ------------------------------------------------------------------ #
    # PhysicalContextPluginBase implementation                            #
    # ------------------------------------------------------------------ #

    def get_physnet_context(self, context, id, fields=None):
        return self._query_physnet_context(context, id)

    def get_physnet_contexts(self, context, filters=None, fields=None,
                             sorts=None, limit=None, marker=None,
                             page_reverse=False):
        raise webob.exc.HTTPNotImplemented()

    def get_switch_context(self, context, id, fields=None):
        physnet = self._resolve_switch_to_physnet(context, id)
        return self._query_physnet_context(context, physnet)

    def get_switch_contexts(self, context, filters=None, fields=None,
                            sorts=None, limit=None, marker=None,
                            page_reverse=False):
        raise webob.exc.HTTPNotImplemented()

    def get_plugin_description(self):
        return ('Provides read-only topology views by physical network '
                'or switch.')

    @classmethod
    def get_plugin_type(cls):
        return ext_pc.PLUGIN_TYPE
