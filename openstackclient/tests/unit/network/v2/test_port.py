#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import argparse
import mock

from mock import call
from osc_lib import exceptions
from osc_lib import utils

from openstackclient.network.v2 import port
from openstackclient.tests.unit.compute.v2 import fakes as compute_fakes
from openstackclient.tests.unit.identity.v3 import fakes as identity_fakes
from openstackclient.tests.unit.network.v2 import fakes as network_fakes
from openstackclient.tests.unit import utils as tests_utils


class TestPort(network_fakes.TestNetworkV2):

    def setUp(self):
        super(TestPort, self).setUp()

        # Get a shortcut to the network client
        self.network = self.app.client_manager.network
        # Get a shortcut to the ProjectManager Mock
        self.projects_mock = self.app.client_manager.identity.projects

    def _get_common_cols_data(self, fake_port):
        columns = (
            'admin_state_up',
            'allowed_address_pairs',
            'binding_host_id',
            'binding_profile',
            'binding_vif_details',
            'binding_vif_type',
            'binding_vnic_type',
            'description',
            'device_id',
            'device_owner',
            'dns_assignment',
            'dns_name',
            'extra_dhcp_opts',
            'fixed_ips',
            'id',
            'mac_address',
            'name',
            'network_id',
            'port_security_enabled',
            'project_id',
            'security_groups',
            'status',
        )

        data = (
            port._format_admin_state(fake_port.admin_state_up),
            utils.format_list_of_dicts(fake_port.allowed_address_pairs),
            fake_port.binding_host_id,
            utils.format_dict(fake_port.binding_profile),
            utils.format_dict(fake_port.binding_vif_details),
            fake_port.binding_vif_type,
            fake_port.binding_vnic_type,
            fake_port.description,
            fake_port.device_id,
            fake_port.device_owner,
            utils.format_list_of_dicts(fake_port.dns_assignment),
            fake_port.dns_name,
            utils.format_list_of_dicts(fake_port.extra_dhcp_opts),
            utils.format_list_of_dicts(fake_port.fixed_ips),
            fake_port.id,
            fake_port.mac_address,
            fake_port.name,
            fake_port.network_id,
            fake_port.port_security_enabled,
            fake_port.project_id,
            utils.format_list(fake_port.security_groups),
            fake_port.status,
        )

        return columns, data


class TestCreatePort(TestPort):

    _port = network_fakes.FakePort.create_one_port()

    def setUp(self):
        super(TestCreatePort, self).setUp()

        self.network.create_port = mock.Mock(return_value=self._port)
        fake_net = network_fakes.FakeNetwork.create_one_network({
            'id': self._port.network_id,
        })
        self.network.find_network = mock.Mock(return_value=fake_net)
        self.fake_subnet = network_fakes.FakeSubnet.create_one_subnet()
        self.network.find_subnet = mock.Mock(return_value=self.fake_subnet)
        # Get the command object to test
        self.cmd = port.CreatePort(self.app, self.namespace)

    def test_create_default_options(self):
        arglist = [
            '--network', self._port.network_id,
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id,),
            ('enable', True),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_full_options(self):
        arglist = [
            '--mac-address', 'aa:aa:aa:aa:aa:aa',
            '--fixed-ip', 'subnet=%s,ip-address=10.0.0.2'
            % self.fake_subnet.id,
            '--description', self._port.description,
            '--device', 'deviceid',
            '--device-owner', 'fakeowner',
            '--disable',
            '--vnic-type', 'macvtap',
            '--binding-profile', 'foo=bar',
            '--binding-profile', 'foo2=bar2',
            '--network', self._port.network_id,
            '--dns-name', '8.8.8.8',
            'test-port',

        ]
        verifylist = [
            ('mac_address', 'aa:aa:aa:aa:aa:aa'),
            (
                'fixed_ip',
                [{'subnet': self.fake_subnet.id, 'ip-address': '10.0.0.2'}]
            ),
            ('description', self._port.description),
            ('device', 'deviceid'),
            ('device_owner', 'fakeowner'),
            ('disable', True),
            ('vnic_type', 'macvtap'),
            ('binding_profile', {'foo': 'bar', 'foo2': 'bar2'}),
            ('network', self._port.network_id),
            ('dns_name', '8.8.8.8'),
            ('name', 'test-port'),

        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'mac_address': 'aa:aa:aa:aa:aa:aa',
            'fixed_ips': [{'subnet_id': self.fake_subnet.id,
                           'ip_address': '10.0.0.2'}],
            'description': self._port.description,
            'device_id': 'deviceid',
            'device_owner': 'fakeowner',
            'admin_state_up': False,
            'binding:vnic_type': 'macvtap',
            'binding:profile': {'foo': 'bar', 'foo2': 'bar2'},
            'network_id': self._port.network_id,
            'dns_name': '8.8.8.8',
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_invalid_json_binding_profile(self):
        arglist = [
            '--network', self._port.network_id,
            '--binding-profile', '{"parent_name":"fake_parent"',
            'test-port',
        ]
        self.assertRaises(argparse.ArgumentTypeError,
                          self.check_parser,
                          self.cmd,
                          arglist,
                          None)

    def test_create_invalid_key_value_binding_profile(self):
        arglist = [
            '--network', self._port.network_id,
            '--binding-profile', 'key',
            'test-port',
        ]
        self.assertRaises(argparse.ArgumentTypeError,
                          self.check_parser,
                          self.cmd,
                          arglist,
                          None)

    def test_create_json_binding_profile(self):
        arglist = [
            '--network', self._port.network_id,
            '--binding-profile', '{"parent_name":"fake_parent"}',
            '--binding-profile', '{"tag":42}',
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id),
            ('enable', True),
            ('binding_profile', {'parent_name': 'fake_parent', 'tag': 42}),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'binding:profile': {'parent_name': 'fake_parent', 'tag': 42},
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_with_security_group(self):
        secgroup = network_fakes.FakeSecurityGroup.create_one_security_group()
        self.network.find_security_group = mock.Mock(return_value=secgroup)
        arglist = [
            '--network', self._port.network_id,
            '--security-group', secgroup.id,
            'test-port',
        ]

        verifylist = [
            ('network', self._port.network_id,),
            ('enable', True),
            ('security_groups', [secgroup.id]),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'security_groups': [secgroup.id],
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_port_with_dns_name(self):
        arglist = [
            '--network', self._port.network_id,
            '--dns-name', '8.8.8.8',
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id,),
            ('enable', True),
            ('dns_name', '8.8.8.8'),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'dns_name': '8.8.8.8',
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_with_security_groups(self):
        sg_1 = network_fakes.FakeSecurityGroup.create_one_security_group()
        sg_2 = network_fakes.FakeSecurityGroup.create_one_security_group()
        self.network.find_security_group = mock.Mock(side_effect=[sg_1, sg_2])
        arglist = [
            '--network', self._port.network_id,
            '--security-group', sg_1.id,
            '--security-group', sg_2.id,
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id,),
            ('enable', True),
            ('security_groups', [sg_1.id, sg_2.id]),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'security_groups': [sg_1.id, sg_2.id],
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_with_no_security_groups(self):
        arglist = [
            '--network', self._port.network_id,
            '--no-security-group',
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id),
            ('enable', True),
            ('no_security_group', True),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'security_groups': [],
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_port_with_allowed_address_pair_ipaddr(self):
        pairs = [{'ip_address': '192.168.1.123'},
                 {'ip_address': '192.168.1.45'}]
        arglist = [
            '--network', self._port.network_id,
            '--allowed-address', 'ip-address=192.168.1.123',
            '--allowed-address', 'ip-address=192.168.1.45',
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id),
            ('enable', True),
            ('allowed_address_pairs', [{'ip-address': '192.168.1.123'},
                                       {'ip-address': '192.168.1.45'}]),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'allowed_address_pairs': pairs,
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_port_with_allowed_address_pair(self):
        pairs = [{'ip_address': '192.168.1.123',
                  'mac_address': 'aa:aa:aa:aa:aa:aa'},
                 {'ip_address': '192.168.1.45',
                  'mac_address': 'aa:aa:aa:aa:aa:b1'}]
        arglist = [
            '--network', self._port.network_id,
            '--allowed-address',
            'ip-address=192.168.1.123,mac-address=aa:aa:aa:aa:aa:aa',
            '--allowed-address',
            'ip-address=192.168.1.45,mac-address=aa:aa:aa:aa:aa:b1',
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id),
            ('enable', True),
            ('allowed_address_pairs', [{'ip-address': '192.168.1.123',
                                        'mac-address': 'aa:aa:aa:aa:aa:aa'},
                                       {'ip-address': '192.168.1.45',
                                        'mac-address': 'aa:aa:aa:aa:aa:b1'}]),
            ('name', 'test-port'),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = (self.cmd.take_action(parsed_args))

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'allowed_address_pairs': pairs,
            'name': 'test-port',
        })

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)

    def test_create_port_security_enabled(self):
        arglist = [
            '--network', self._port.network_id,
            '--enable-port-security',
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id,),
            ('enable', True),
            ('enable_port_security', True),
            ('name', 'test-port'),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'port_security_enabled': True,
            'name': 'test-port',
        })

    def test_create_port_security_disabled(self):
        arglist = [
            '--network', self._port.network_id,
            '--disable-port-security',
            'test-port',
        ]
        verifylist = [
            ('network', self._port.network_id,),
            ('enable', True),
            ('disable_port_security', True),
            ('name', 'test-port'),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        self.network.create_port.assert_called_once_with(**{
            'admin_state_up': True,
            'network_id': self._port.network_id,
            'port_security_enabled': False,
            'name': 'test-port',
        })


class TestDeletePort(TestPort):

    # Ports to delete.
    _ports = network_fakes.FakePort.create_ports(count=2)

    def setUp(self):
        super(TestDeletePort, self).setUp()

        self.network.delete_port = mock.Mock(return_value=None)
        self.network.find_port = network_fakes.FakePort.get_ports(
            ports=self._ports)
        # Get the command object to test
        self.cmd = port.DeletePort(self.app, self.namespace)

    def test_port_delete(self):
        arglist = [
            self._ports[0].name,
        ]
        verifylist = [
            ('port', [self._ports[0].name]),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        result = self.cmd.take_action(parsed_args)
        self.network.find_port.assert_called_once_with(
            self._ports[0].name, ignore_missing=False)
        self.network.delete_port.assert_called_once_with(self._ports[0])
        self.assertIsNone(result)

    def test_multi_ports_delete(self):
        arglist = []
        verifylist = []

        for p in self._ports:
            arglist.append(p.name)
        verifylist = [
            ('port', arglist),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        result = self.cmd.take_action(parsed_args)

        calls = []
        for p in self._ports:
            calls.append(call(p))
        self.network.delete_port.assert_has_calls(calls)
        self.assertIsNone(result)

    def test_multi_ports_delete_with_exception(self):
        arglist = [
            self._ports[0].name,
            'unexist_port',
        ]
        verifylist = [
            ('port',
             [self._ports[0].name, 'unexist_port']),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        find_mock_result = [self._ports[0], exceptions.CommandError]
        self.network.find_port = (
            mock.Mock(side_effect=find_mock_result)
        )

        try:
            self.cmd.take_action(parsed_args)
            self.fail('CommandError should be raised.')
        except exceptions.CommandError as e:
            self.assertEqual('1 of 2 ports failed to delete.', str(e))

        self.network.find_port.assert_any_call(
            self._ports[0].name, ignore_missing=False)
        self.network.find_port.assert_any_call(
            'unexist_port', ignore_missing=False)
        self.network.delete_port.assert_called_once_with(
            self._ports[0]
        )


class TestListPort(TestPort):

    _ports = network_fakes.FakePort.create_ports(count=3)

    columns = (
        'ID',
        'Name',
        'MAC Address',
        'Fixed IP Addresses',
        'Status',
    )

    columns_long = (
        'ID',
        'Name',
        'MAC Address',
        'Fixed IP Addresses',
        'Status',
        'Security Groups',
        'Device Owner',
    )

    data = []
    for prt in _ports:
        data.append((
            prt.id,
            prt.name,
            prt.mac_address,
            utils.format_list_of_dicts(prt.fixed_ips),
            prt.status,
        ))

    data_long = []
    for prt in _ports:
        data_long.append((
            prt.id,
            prt.name,
            prt.mac_address,
            utils.format_list_of_dicts(prt.fixed_ips),
            prt.status,
            utils.format_list(prt.security_groups),
            prt.device_owner,
        ))

    def setUp(self):
        super(TestListPort, self).setUp()

        # Get the command object to test
        self.cmd = port.ListPort(self.app, self.namespace)
        self.network.ports = mock.Mock(return_value=self._ports)
        fake_router = network_fakes.FakeRouter.create_one_router({
            'id': 'fake-router-id',
        })
        fake_network = network_fakes.FakeNetwork.create_one_network({
            'id': 'fake-network-id',
        })
        self.network.find_router = mock.Mock(return_value=fake_router)
        self.network.find_network = mock.Mock(return_value=fake_network)
        self.app.client_manager.compute = mock.Mock()

    def test_port_list_no_options(self):
        arglist = []
        verifylist = []

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        self.network.ports.assert_called_once_with()
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))

    def test_port_list_router_opt(self):
        arglist = [
            '--router', 'fake-router-name',
        ]

        verifylist = [
            ('router', 'fake-router-name')
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        self.network.ports.assert_called_once_with(**{
            'device_id': 'fake-router-id'
        })
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))

    @mock.patch.object(utils, 'find_resource')
    def test_port_list_with_server_option(self, mock_find):
        fake_server = compute_fakes.FakeServer.create_one_server()
        mock_find.return_value = fake_server

        arglist = [
            '--server', 'fake-server-name',
        ]
        verifylist = [
            ('server', 'fake-server-name'),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        columns, data = self.cmd.take_action(parsed_args)
        self.network.ports.assert_called_once_with(
            device_id=fake_server.id)
        mock_find.assert_called_once_with(mock.ANY, 'fake-server-name')
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))

    def test_port_list_device_owner_opt(self):
        arglist = [
            '--device-owner', self._ports[0].device_owner,
        ]

        verifylist = [
            ('device_owner', self._ports[0].device_owner)
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        self.network.ports.assert_called_once_with(**{
            'device_owner': self._ports[0].device_owner
        })
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))

    def test_port_list_all_opt(self):
        arglist = [
            '--device-owner', self._ports[0].device_owner,
            '--router', 'fake-router-name',
            '--network', 'fake-network-name',
            '--mac-address', self._ports[0].mac_address,
        ]

        verifylist = [
            ('device_owner', self._ports[0].device_owner),
            ('router', 'fake-router-name'),
            ('network', 'fake-network-name'),
            ('mac_address', self._ports[0].mac_address)
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        self.network.ports.assert_called_once_with(**{
            'device_owner': self._ports[0].device_owner,
            'device_id': 'fake-router-id',
            'network_id': 'fake-network-id',
            'mac_address': self._ports[0].mac_address
        })
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))

    def test_port_list_mac_address_opt(self):
        arglist = [
            '--mac-address', self._ports[0].mac_address,
        ]

        verifylist = [
            ('mac_address', self._ports[0].mac_address)
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        self.network.ports.assert_called_once_with(**{
            'mac_address': self._ports[0].mac_address
        })
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))

    def test_list_port_with_long(self):
        arglist = [
            '--long',
        ]

        verifylist = [
            ('long', True),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        self.network.ports.assert_called_once_with()
        self.assertEqual(self.columns_long, columns)
        self.assertEqual(self.data_long, list(data))

    def test_port_list_project(self):
        project = identity_fakes.FakeProject.create_one_project()
        self.projects_mock.get.return_value = project
        arglist = [
            '--project', project.id,
        ]
        verifylist = [
            ('project', project.id),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)
        filters = {'tenant_id': project.id, 'project_id': project.id}

        self.network.ports.assert_called_once_with(**filters)
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))

    def test_port_list_project_domain(self):
        project = identity_fakes.FakeProject.create_one_project()
        self.projects_mock.get.return_value = project
        arglist = [
            '--project', project.id,
            '--project-domain', project.domain_id,
        ]
        verifylist = [
            ('project', project.id),
            ('project_domain', project.domain_id),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)
        filters = {'tenant_id': project.id, 'project_id': project.id}

        self.network.ports.assert_called_once_with(**filters)
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, list(data))


class TestSetPort(TestPort):

    _port = network_fakes.FakePort.create_one_port()

    def setUp(self):
        super(TestSetPort, self).setUp()
        self.fake_subnet = network_fakes.FakeSubnet.create_one_subnet()
        self.network.find_subnet = mock.Mock(return_value=self.fake_subnet)
        self.network.find_port = mock.Mock(return_value=self._port)
        self.network.update_port = mock.Mock(return_value=None)

        # Get the command object to test
        self.cmd = port.SetPort(self.app, self.namespace)

    def test_set_fixed_ip(self):
        arglist = [
            '--fixed-ip', 'ip-address=10.0.0.11',
            self._port.name,
        ]
        verifylist = [
            ('fixed_ip', [{'ip-address': '10.0.0.11'}]),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'fixed_ips': [{'ip_address': '10.0.0.11'}],
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_set_dns_name(self):
        arglist = [
            '--dns-name', '8.8.8.8',
            self._port.name,
        ]
        verifylist = [
            ('dns_name', '8.8.8.8'),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'dns_name': '8.8.8.8',
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_append_fixed_ip(self):
        _testport = network_fakes.FakePort.create_one_port(
            {'fixed_ips': [{'ip_address': '0.0.0.1'}]})
        self.network.find_port = mock.Mock(return_value=_testport)
        arglist = [
            '--fixed-ip', 'ip-address=10.0.0.12',
            _testport.name,
        ]
        verifylist = [
            ('fixed_ip', [{'ip-address': '10.0.0.12'}]),
            ('port', _testport.name),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)
        attrs = {
            'fixed_ips': [
                {'ip_address': '10.0.0.12'}, {'ip_address': '0.0.0.1'}],
        }
        self.network.update_port.assert_called_once_with(_testport, **attrs)
        self.assertIsNone(result)

    def test_overwrite_binding_profile(self):
        _testport = network_fakes.FakePort.create_one_port(
            {'binding_profile': {'lok_i': 'visi_on'}})
        self.network.find_port = mock.Mock(return_value=_testport)
        arglist = [
            '--binding-profile', 'lok_i=than_os',
            '--no-binding-profile',
            _testport.name,
        ]
        verifylist = [
            ('binding_profile', {'lok_i': 'than_os'}),
            ('no_binding_profile', True)
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)
        attrs = {
            'binding:profile':
                {'lok_i': 'than_os'},
        }
        self.network.update_port.assert_called_once_with(_testport, **attrs)
        self.assertIsNone(result)

    def test_overwrite_fixed_ip(self):
        _testport = network_fakes.FakePort.create_one_port(
            {'fixed_ips': [{'ip_address': '0.0.0.1'}]})
        self.network.find_port = mock.Mock(return_value=_testport)
        arglist = [
            '--fixed-ip', 'ip-address=10.0.0.12',
            '--no-fixed-ip',
            _testport.name,
        ]
        verifylist = [
            ('fixed_ip', [{'ip-address': '10.0.0.12'}]),
            ('no_fixed_ip', True)
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)
        attrs = {
            'fixed_ips': [
                {'ip_address': '10.0.0.12'}],
        }
        self.network.update_port.assert_called_once_with(_testport, **attrs)
        self.assertIsNone(result)

    def test_set_this(self):
        arglist = [
            '--disable',
            '--no-fixed-ip',
            '--no-binding-profile',
            self._port.name,
        ]
        verifylist = [
            ('disable', True),
            ('no_binding_profile', True),
            ('no_fixed_ip', True),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'admin_state_up': False,
            'binding:profile': {},
            'fixed_ips': [],
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_set_that(self):
        arglist = [
            '--description', 'newDescription',
            '--enable',
            '--vnic-type', 'macvtap',
            '--binding-profile', 'foo=bar',
            '--host', 'binding-host-id-xxxx',
            '--name', 'newName',
            self._port.name,
        ]
        verifylist = [
            ('description', 'newDescription'),
            ('enable', True),
            ('vnic_type', 'macvtap'),
            ('binding_profile', {'foo': 'bar'}),
            ('host', 'binding-host-id-xxxx'),
            ('name', 'newName'),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'admin_state_up': True,
            'binding:vnic_type': 'macvtap',
            'binding:profile': {'foo': 'bar'},
            'binding:host_id': 'binding-host-id-xxxx',
            'description': 'newDescription',
            'name': 'newName',
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_set_nothing(self):
        arglist = [
            self._port.name,
        ]
        verifylist = [
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {}
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_set_invalid_json_binding_profile(self):
        arglist = [
            '--binding-profile', '{"parent_name"}',
            'test-port',
        ]
        self.assertRaises(argparse.ArgumentTypeError,
                          self.check_parser,
                          self.cmd,
                          arglist,
                          None)

    def test_set_invalid_key_value_binding_profile(self):
        arglist = [
            '--binding-profile', 'key',
            'test-port',
        ]
        self.assertRaises(argparse.ArgumentTypeError,
                          self.check_parser,
                          self.cmd,
                          arglist,
                          None)

    def test_set_mixed_binding_profile(self):
        arglist = [
            '--binding-profile', 'foo=bar',
            '--binding-profile', '{"foo2": "bar2"}',
            self._port.name,
        ]
        verifylist = [
            ('binding_profile', {'foo': 'bar', 'foo2': 'bar2'}),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'binding:profile': {'foo': 'bar', 'foo2': 'bar2'},
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_set_security_group(self):
        sg = network_fakes.FakeSecurityGroup.create_one_security_group()
        self.network.find_security_group = mock.Mock(return_value=sg)
        arglist = [
            '--security-group', sg.id,
            self._port.name,
        ]
        verifylist = [
            ('security_groups', [sg.id]),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'security_groups': [sg.id],
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_append_security_group(self):
        sg_1 = network_fakes.FakeSecurityGroup.create_one_security_group()
        sg_2 = network_fakes.FakeSecurityGroup.create_one_security_group()
        sg_3 = network_fakes.FakeSecurityGroup.create_one_security_group()
        self.network.find_security_group = mock.Mock(side_effect=[sg_2, sg_3])
        _testport = network_fakes.FakePort.create_one_port(
            {'security_groups': [sg_1.id]})
        self.network.find_port = mock.Mock(return_value=_testport)
        arglist = [
            '--security-group', sg_2.id,
            '--security-group', sg_3.id,
            _testport.name,
        ]
        verifylist = [
            ('security_groups', [sg_2.id, sg_3.id]),
            ('port', _testport.name),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)
        attrs = {
            'security_groups': [sg_1.id, sg_2.id, sg_3.id],
        }
        self.network.update_port.assert_called_once_with(_testport, **attrs)
        self.assertIsNone(result)

    def test_set_no_security_groups(self):
        arglist = [
            '--no-security-group',
            self._port.name,
        ]
        verifylist = [
            ('no_security_group', True),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'security_groups': [],
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_overwrite_security_group(self):
        sg1 = network_fakes.FakeSecurityGroup.create_one_security_group()
        sg2 = network_fakes.FakeSecurityGroup.create_one_security_group()
        _testport = network_fakes.FakePort.create_one_port(
            {'security_groups': [sg1.id]})
        self.network.find_port = mock.Mock(return_value=_testport)
        self.network.find_security_group = mock.Mock(return_value=sg2)
        arglist = [
            '--security-group', sg2.id,
            '--no-security-group',
            _testport.name,
        ]
        verifylist = [
            ('security_groups', [sg2.id]),
            ('no_security_group', True)
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)
        attrs = {
            'security_groups': [sg2.id],
        }
        self.network.update_port.assert_called_once_with(_testport, **attrs)
        self.assertIsNone(result)

    def test_set_allowed_address_pair(self):
        arglist = [
            '--allowed-address', 'ip-address=192.168.1.123',
            self._port.name,
        ]
        verifylist = [
            ('allowed_address_pairs', [{'ip-address': '192.168.1.123'}]),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'allowed_address_pairs': [{'ip_address': '192.168.1.123'}],
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_append_allowed_address_pair(self):
        _testport = network_fakes.FakePort.create_one_port(
            {'allowed_address_pairs': [{'ip_address': '192.168.1.123'}]})
        self.network.find_port = mock.Mock(return_value=_testport)
        arglist = [
            '--allowed-address', 'ip-address=192.168.1.45',
            _testport.name,
        ]
        verifylist = [
            ('allowed_address_pairs', [{'ip-address': '192.168.1.45'}]),
            ('port', _testport.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'allowed_address_pairs': [{'ip_address': '192.168.1.123'},
                                      {'ip_address': '192.168.1.45'}],
        }
        self.network.update_port.assert_called_once_with(_testport, **attrs)
        self.assertIsNone(result)

    def test_overwrite_allowed_address_pair(self):
        _testport = network_fakes.FakePort.create_one_port(
            {'allowed_address_pairs': [{'ip_address': '192.168.1.123'}]})
        self.network.find_port = mock.Mock(return_value=_testport)
        arglist = [
            '--allowed-address', 'ip-address=192.168.1.45',
            '--no-allowed-address',
            _testport.name,
        ]
        verifylist = [
            ('allowed_address_pairs', [{'ip-address': '192.168.1.45'}]),
            ('no_allowed_address_pair', True),
            ('port', _testport.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'allowed_address_pairs': [{'ip_address': '192.168.1.45'}],
        }
        self.network.update_port.assert_called_once_with(_testport, **attrs)
        self.assertIsNone(result)

    def test_set_no_allowed_address_pairs(self):
        arglist = [
            '--no-allowed-address',
            self._port.name,
        ]
        verifylist = [
            ('no_allowed_address_pair', True),
            ('port', self._port.name),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'allowed_address_pairs': [],
        }
        self.network.update_port.assert_called_once_with(self._port, **attrs)
        self.assertIsNone(result)

    def test_port_security_enabled(self):
        arglist = [
            '--enable-port-security',
            self._port.id,
        ]
        verifylist = [
            ('enable_port_security', True),
            ('port', self._port.id,)
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        self.network.update_port.assert_called_once_with(self._port, **{
            'port_security_enabled': True,
        })

    def test_port_security_disabled(self):
        arglist = [
            '--disable-port-security',
            self._port.id,
        ]
        verifylist = [
            ('disable_port_security', True),
            ('port', self._port.id,)
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        self.network.update_port.assert_called_once_with(self._port, **{
            'port_security_enabled': False,
        })


class TestShowPort(TestPort):

    # The port to show.
    _port = network_fakes.FakePort.create_one_port()

    def setUp(self):
        super(TestShowPort, self).setUp()

        self.network.find_port = mock.Mock(return_value=self._port)

        # Get the command object to test
        self.cmd = port.ShowPort(self.app, self.namespace)

    def test_show_no_options(self):
        arglist = []
        verifylist = []

        self.assertRaises(tests_utils.ParserException,
                          self.check_parser, self.cmd, arglist, verifylist)

    def test_show_all_options(self):
        arglist = [
            self._port.name,
        ]
        verifylist = [
            ('port', self._port.name),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        self.network.find_port.assert_called_once_with(
            self._port.name, ignore_missing=False)

        ref_columns, ref_data = self._get_common_cols_data(self._port)
        self.assertEqual(ref_columns, columns)
        self.assertEqual(ref_data, data)


class TestUnsetPort(TestPort):

    def setUp(self):
        super(TestUnsetPort, self).setUp()
        self._testport = network_fakes.FakePort.create_one_port(
            {'fixed_ips': [{'subnet_id': '042eb10a-3a18-4658-ab-cf47c8d03152',
                            'ip_address': '0.0.0.1'},
                           {'subnet_id': '042eb10a-3a18-4658-ab-cf47c8d03152',
                            'ip_address': '1.0.0.0'}],
             'binding:profile': {'batman': 'Joker', 'Superman': 'LexLuthor'}})
        self.fake_subnet = network_fakes.FakeSubnet.create_one_subnet(
            {'id': '042eb10a-3a18-4658-ab-cf47c8d03152'})
        self.network.find_subnet = mock.Mock(return_value=self.fake_subnet)
        self.network.find_port = mock.Mock(return_value=self._testport)
        self.network.update_port = mock.Mock(return_value=None)
        # Get the command object to test
        self.cmd = port.UnsetPort(self.app, self.namespace)

    def test_unset_port_parameters(self):
        arglist = [
            '--fixed-ip',
            'subnet=042eb10a-3a18-4658-ab-cf47c8d03152,ip-address=1.0.0.0',
            '--binding-profile', 'Superman',
            self._testport.name,
        ]
        verifylist = [
            ('fixed_ip', [{
                'subnet': '042eb10a-3a18-4658-ab-cf47c8d03152',
                'ip-address': '1.0.0.0'}]),
            ('binding_profile', ['Superman']),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'fixed_ips': [{
                'subnet_id': '042eb10a-3a18-4658-ab-cf47c8d03152',
                'ip_address': '0.0.0.1'}],
            'binding:profile': {'batman': 'Joker'}
        }
        self.network.update_port.assert_called_once_with(
            self._testport, **attrs)
        self.assertIsNone(result)

    def test_unset_port_fixed_ip_not_existent(self):
        arglist = [
            '--fixed-ip', 'ip-address=1.0.0.1',
            '--binding-profile', 'Superman',
            self._testport.name,
        ]
        verifylist = [
            ('fixed_ip', [{'ip-address': '1.0.0.1'}]),
            ('binding_profile', ['Superman']),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.assertRaises(exceptions.CommandError,
                          self.cmd.take_action,
                          parsed_args)

    def test_unset_port_binding_profile_not_existent(self):
        arglist = [
            '--fixed-ip', 'ip-address=1.0.0.0',
            '--binding-profile', 'Neo',
            self._testport.name,
        ]
        verifylist = [
            ('fixed_ip', [{'ip-address': '1.0.0.0'}]),
            ('binding_profile', ['Neo']),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.assertRaises(exceptions.CommandError,
                          self.cmd.take_action,
                          parsed_args)

    def test_unset_security_group(self):
        _fake_sg1 = network_fakes.FakeSecurityGroup.create_one_security_group()
        _fake_sg2 = network_fakes.FakeSecurityGroup.create_one_security_group()
        _fake_port = network_fakes.FakePort.create_one_port(
            {'security_groups': [_fake_sg1.id, _fake_sg2.id]})
        self.network.find_port = mock.Mock(return_value=_fake_port)
        self.network.find_security_group = mock.Mock(return_value=_fake_sg2)
        arglist = [
            '--security-group', _fake_sg2.id,
            _fake_port.name,
        ]
        verifylist = [
            ('security_groups', [_fake_sg2.id]),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'security_groups': [_fake_sg1.id]
        }
        self.network.update_port.assert_called_once_with(
            _fake_port, **attrs)
        self.assertIsNone(result)

    def test_unset_port_security_group_not_existent(self):
        _fake_sg1 = network_fakes.FakeSecurityGroup.create_one_security_group()
        _fake_sg2 = network_fakes.FakeSecurityGroup.create_one_security_group()
        _fake_port = network_fakes.FakePort.create_one_port(
            {'security_groups': [_fake_sg1.id]})
        self.network.find_security_group = mock.Mock(return_value=_fake_sg2)
        arglist = [
            '--security-group', _fake_sg2.id,
            _fake_port.name,
        ]
        verifylist = [
            ('security_groups', [_fake_sg2.id]),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.assertRaises(exceptions.CommandError,
                          self.cmd.take_action,
                          parsed_args)

    def test_unset_port_allowed_address_pair(self):
        _fake_port = network_fakes.FakePort.create_one_port(
            {'allowed_address_pairs': [{'ip_address': '192.168.1.123'}]})
        self.network.find_port = mock.Mock(return_value=_fake_port)
        arglist = [
            '--allowed-address', 'ip-address=192.168.1.123',
            _fake_port.name,
        ]
        verifylist = [
            ('allowed_address_pairs', [{'ip-address': '192.168.1.123'}]),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        result = self.cmd.take_action(parsed_args)

        attrs = {
            'allowed_address_pairs': [],
        }

        self.network.update_port.assert_called_once_with(_fake_port, **attrs)
        self.assertIsNone(result)

    def test_unset_port_allowed_address_pair_not_existent(self):
        _fake_port = network_fakes.FakePort.create_one_port(
            {'allowed_address_pairs': [{'ip_address': '192.168.1.123'}]})
        self.network.find_port = mock.Mock(return_value=_fake_port)
        arglist = [
            '--allowed-address', 'ip-address=192.168.1.45',
            _fake_port.name,
        ]
        verifylist = [
            ('allowed_address_pairs', [{'ip-address': '192.168.1.45'}]),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.assertRaises(exceptions.CommandError,
                          self.cmd.take_action,
                          parsed_args)
