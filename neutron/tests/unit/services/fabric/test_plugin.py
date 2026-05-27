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

from neutron_lib import context
from neutron_lib import exceptions as lib_exc
from oslo_config import cfg

from neutron.services.fabric import plugin as fabric_plugin
from neutron.tests.common import test_db_base_plugin_v2 as test_plugin
from neutron.tests.unit import testlib_api

SERVICE_PLUGIN_KLASS = 'neutron.services.fabric.plugin.FabricPlugin'


class TestFabricPlugin(testlib_api.SqlTestCase):

    _fabric_data = {
        'name': 'test-fabric',
        'physical_network': 'physnet1',
        'shared': True,
        'project_id': test_plugin.TEST_PROJECT_ID,
    }

    _private_fabric_data = {
        'name': 'private-fabric',
        'physical_network': 'physnet2',
        'shared': False,
        'project_id': test_plugin.TEST_PROJECT_ID,
    }

    def setUp(self):
        super().setUp()
        self.plugin = fabric_plugin.FabricPlugin()
        self.context = context.get_admin_context()
        cfg.CONF.set_override('service_plugins', [SERVICE_PLUGIN_KLASS])

    def test_create_fabric(self):
        fabric = {'fabric': self._fabric_data}
        ret = self.plugin.create_fabric(self.context, fabric)
        self.assertEqual('physnet1', ret['physical_network'])
        self.assertTrue(ret['shared'])
        self.assertEqual('test-fabric', ret['name'])

    def test_create_fabric_private(self):
        fabric = {'fabric': self._private_fabric_data}
        ret = self.plugin.create_fabric(self.context, fabric)
        self.assertEqual('physnet2', ret['physical_network'])
        self.assertFalse(ret['shared'])
        self.assertEqual(test_plugin.TEST_PROJECT_ID, ret['project_id'])

    def test_create_fabric_shared_has_no_project_id(self):
        fabric = {'fabric': self._fabric_data}
        ret = self.plugin.create_fabric(self.context, fabric)
        self.assertIsNone(ret['project_id'])

    def test_get_fabric(self):
        fabric = {'fabric': self._fabric_data}
        created = self.plugin.create_fabric(self.context, fabric)
        fetched = self.plugin.get_fabric(self.context, created['id'])
        self.assertEqual(created['id'], fetched['id'])
        self.assertEqual('physnet1', fetched['physical_network'])

    def test_get_fabric_not_found(self):
        self.assertRaises(
            lib_exc.ObjectNotFound,
            self.plugin.get_fabric,
            self.context,
            'nonexistent-uuid')

    def test_get_fabrics(self):
        for physnet in ('physnet1', 'physnet2'):
            data = dict(self._fabric_data, physical_network=physnet,
                        name=physnet)
            self.plugin.create_fabric(self.context, {'fabric': data})
        fabrics = self.plugin.get_fabrics(self.context)
        self.assertEqual(2, len(fabrics))

    def test_delete_fabric(self):
        fabric = {'fabric': self._fabric_data}
        created = self.plugin.create_fabric(self.context, fabric)
        self.plugin.delete_fabric(self.context, created['id'])
        self.assertRaises(
            lib_exc.ObjectNotFound,
            self.plugin.get_fabric,
            self.context,
            created['id'])

    def test_update_fabric_name(self):
        fabric = {'fabric': self._fabric_data}
        created = self.plugin.create_fabric(self.context, fabric)
        updated = self.plugin.update_fabric(
            self.context, created['id'],
            {'fabric': {'name': 'renamed'}})
        self.assertEqual('renamed', updated['name'])
        self.assertEqual('physnet1', updated['physical_network'])
