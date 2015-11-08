# Copyright 2015 Hewlett-Packard Corporation
# All Rights Reserved.
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

import copy
import datetime
import mock
import novaclient.exceptions
import novaclient.v2.servers as novaclient_servers

from searchlight.elasticsearch.plugins.nova import\
    servers as servers_plugin
import searchlight.tests.unit.utils as unit_test_utils
import searchlight.tests.utils as test_utils


USER1 = u'27f4d76b-be62-4e4e-aa33bb11cc55'

TENANT1 = u'4d64ac83-87af-4d2a-b884-cc42c3e8f2c0'
TENANT2 = u'c6993374-7c4b-4f18-b317-85e3acdfd259'

# Instances
ID1 = u'6c41b4d1-f0fa-42d6-9d8d-e3b99695aa69'
ID2 = u'08ca6c43-eea8-48d0-bbb2-30c50109d5d8'
ID3 = u'a380287d-1f61-4887-959c-8c5ab8f75f8f'


flavor1 = {
    u'id': '1',
    u'links': [{
        u'href': u'http://localhost:8774/dontcare',
        u'rel': u'bookmark'
    }]
}
flavor2 = {
    u'id': '2',
    u'links': [{
        u'href': u'http://localhost:8774/stilldontcare',
        u'rel': u'bookmark'
    }]
}

imagea = {
    u'id': u'a',
    u'links': [{
        u'href': u'http://localhost:8774/dontcare',
        u'rel': u'bookmark'
    }]
}
imageb = {
    u'id': u'b',
    u'links': [{
        u'href': u'http://localhost:8774/dontcare',
        u'rel': u'bookmark'
    }]
}

net_ip4_6 = {
    u'net4_6': [
        {
            u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
            u'version': 4,
            u'addr': u'0.0.0.0',
            u'OS-EXT-IPS:type': u'fixed'
        },
        {
            u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
            u'version': 6,
            u'addr': u'::1',
            u'OS-EXT-IPS:type': u'fixed'
        }
    ],
    u'net4': [
        {
            u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
            u'version': 4,
            u'addr': u'127.0.0.1',
            u'OS-EXT-IPS:type': u'fixed'
        }
    ]
}
net_ipv4 = {u'net4': [dict(net_ip4_6[u'net4'][0])]}

_now = datetime.datetime.utcnow()
_five_minutes_ago = _now - datetime.timedelta(minutes=5)
created_now = _five_minutes_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
updated_now = _now.strftime('%Y-%m-%dT%H:%M:%SZ')

nova_server_getter = 'novaclient.v2.client.servers.ServerManager.get'


def _instance_fixture(instance_id, name, tenant_id, **kwargs):
    # A full nova v2 server.get output
    attrs = {
        u'OS-DCF:diskConfig': u'MANUAL',
        u'OS-EXT-AZ:availability_zone': u'nova',
        u'OS-EXT-SRV-ATTR:host': u'devstack',
        u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'devstack',
        u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000001',
        u'OS-EXT-STS:power_state': 1,
        u'OS-EXT-STS:task_state': None,
        u'OS-EXT-STS:vm_state': u'active',
        u'OS-SRV-USG:launched_at': created_now,
        u'OS-SRV-USG:terminated_at': None,
        u'accessIPv4': u'',
        u'accessIPv6': u'',
        u'addresses': {
            u'public': [{
                u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
                u'OS-EXT-IPS:type': u'fixed',
                u'addr': u'172.25.0.3',
                u'version': 4
            }, {
                u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
                u'OS-EXT-IPS:type': u'fixed',
                u'addr': u'2001:db8::3',
                u'version': 6
            }]
        },
        u'config_drive': u'True',
        u'created': created_now,
        u'flavor': {
            u'id': u'1',
            u'links': [{
                u'href': u'http://localhost:8774/dontcare',
                u'rel': u'bookmark'
            }]
        },
        u'hostId': u'd86d2c042a1f233227f70c5e9d2c5829de98d222d0922f469054ac17',
        u'id': instance_id,
        u'image': {
            u'id': u'46b77e67-ce40-44ca-823d-e6f83489f21e',
            u'links': [{
                u'href': u'http://localhost:8774/dontcare',
                u'rel': u'bookmark'
            }]
        },
        u'key_name': u'key',
        u'links': [
            {
                u'href': u'http://localhost:8774/dontcare',
                u'rel': u'self'
            },
            {
                u'href': u'http://localhost:8774/dontcare',
                u'rel': u'bookmark'
            }
        ],
        u'metadata': {},
        u'name': name,
        u'os-extended-volumes:volumes_attached': [],
        u'progress': 0,
        u'security_groups': [{u'name': u'default'}],
        u'status': u'ACTIVE',
        u'tenant_id': tenant_id,
        u'updated': updated_now,
        u'user_id': USER1}

    attrs.update(kwargs)
    server = mock.Mock(spec=novaclient_servers.Server, **attrs)
    server.to_dict.return_value = attrs
    return server


class TestServerLoaderPlugin(test_utils.BaseTestCase):
    def setUp(self):
        super(TestServerLoaderPlugin, self).setUp()
        self.plugin = servers_plugin.ServerIndex()
        self._create_fixtures()

    def _create_fixtures(self):
        self.instance1 = _instance_fixture(
            ID1, u'instance1', tenant_id=TENANT1,
            flavor=flavor1, image=imagea, addresses=net_ipv4,
            **{u'OS-EXT-AZ:availability_zone': u'az1',
               u'OS-EXT-SRV-ATTR:host': u'host1',
               u'hostId': u'host1'})
        self.instance2 = _instance_fixture(
            ID2, 'instance2', tenant_id=TENANT2,
            flavor=flavor2, image=imageb, addresses=net_ip4_6)
        self.instances = [self.instance1, self.instance2]

    def test_index_name(self):
        self.assertEqual('searchlight', self.plugin.get_index_name())

    def test_document_type(self):
        self.assertEqual('OS::Nova::Server', self.plugin.get_document_type())

    def test_serialize(self):
        expected = {
            u'OS-DCF:diskConfig': u'MANUAL',
            u'OS-EXT-AZ:availability_zone': u'az1',
            u'OS-EXT-SRV-ATTR:host': u'host1',
            u'OS-EXT-SRV-ATTR:hypervisor_hostname': u'devstack',
            u'OS-EXT-SRV-ATTR:instance_name': u'instance-00000001',
            u'OS-EXT-STS:power_state': 1,
            u'OS-EXT-STS:task_state': None,
            u'OS-EXT-STS:vm_state': u'active',
            u'OS-SRV-USG:launched_at': created_now,
            u'OS-SRV-USG:terminated_at': None,
            u'accessIPv4': u'',
            u'accessIPv6': u'',
            u'addresses': {
                u'public': [{
                    u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
                    u'OS-EXT-IPS:type': u'fixed',
                    u'addr': u'172.25.0.3',
                    u'version': 4
                }, {
                    u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
                    u'OS-EXT-IPS:type': u'fixed',
                    u'addr': u'2001:db8::3',
                    u'version': 6
                }]
            },
            u'config_drive': u'True',
            u'flavor': {u'id': u'1'},
            u'hostId': u'host1',
            u'id': u'6c41b4d1-f0fa-42d6-9d8d-e3b99695aa69',
            u'image': {u'id': u'a'},
            u'key_name': u'key',
            u'metadata': {},
            u'name': u'instance1',
            u'os-extended-volumes:volumes_attached': [],
            u'owner': u'4d64ac83-87af-4d2a-b884-cc42c3e8f2c0',
            u'security_groups': [{u'name': u'default'}],
            u'status': u'ACTIVE',
            u'tenant_id': u'4d64ac83-87af-4d2a-b884-cc42c3e8f2c0',
            u'updated': updated_now,
            u'user_id': u'27f4d76b-be62-4e4e-aa33bb11cc55',
            u'networks': [{
                u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:1e:37:32',
                u'version': 4,
                u'ipv4_addr': u'127.0.0.1',
                u'OS-EXT-IPS:type': u'fixed',
                u'name': u'net4',
            }],
            u'addresses': net_ipv4,
            u'created': created_now,
            u'created_at': created_now,
            u'updated': updated_now,
            u'updated_at': updated_now,
        }
        with mock.patch(nova_server_getter, return_value=self.instance1):
            serialized = self.plugin.serialize(self.instance1.id)

        self.assertEqual(expected, serialized)

    def test_protected_properties(self):
        with mock.patch(nova_server_getter, return_value=self.instance1):
            serialized = self.plugin.serialize(self.instance1.id)

        elasticsearch_results = {
            'hits': {
                'hits': [{
                    '_source': copy.deepcopy(serialized),
                    '_type': self.plugin.get_document_type(),
                    '_index': self.plugin.get_index_name()
                }]
            }
        }

        protected_fields = (u'OS-EXT-SRV-ATTR:host',
                            u'OS-EXT-SRV-ATTR:hypervisor_hostname')

        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search', is_admin=True
        )
        self.plugin.filter_result(elasticsearch_results['hits']['hits'][0],
                                  fake_request.context)

        # Result should contain all the fields
        single_result = elasticsearch_results['hits']['hits'][0]['_source']
        self.assertEqual(serialized, single_result)
        for field in protected_fields:
            self.assertTrue(field in single_result)

        # Refresh the mock results since they can be modified in-place
        elasticsearch_results = {
            'hits': {
                'hits': [{
                    '_source': copy.deepcopy(serialized),
                    '_type': self.plugin.get_document_type(),
                    '_index': self.plugin.get_index_name()
                }]
            }
        }
        # Make the same request as a non-admin
        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search', is_admin=False
        )

        self.plugin.filter_result(elasticsearch_results['hits']['hits'][0],
                                  fake_request.context)

        single_result = elasticsearch_results['hits']['hits'][0]['_source']

        for field in protected_fields:
            self.assertFalse(field in single_result)

    def test_update_deleted(self):
        """Test that if a server has been deleted it's deleted from the index
        if an update notification's received.
        """
        mock_engine = mock.Mock()
        self.plugin.engine = mock_engine

        with mock.patch(nova_server_getter,
                        side_effect=novaclient.exceptions.NotFound('testing')):
            self.plugin.get_notification_handler().create_or_update(
                {u'instance_id': u'missing'}
            )

            self.assertTrue(not mock_engine.index.called)
            mock_engine.delete.assert_called_once_with(
                index=self.plugin.get_index_name(),
                doc_type=self.plugin.get_document_type(),
                id=u'missing')

    def test_facets_non_admin(self):
        mock_engine = mock.Mock()
        self.plugin.engine = mock_engine

        mock_engine.search.return_value = {
            'aggregations': {
                'status': {'buckets': [{'key': 'ACTIVE', 'doc_count': 2}]},
                'OS-EXT-AZ:availability_zone': {'buckets': []},
                'image.id': {'buckets': [{'key': imagea['id'],
                                          'doc_count': 1}]},
                'flavor.id': {'buckets': [{'key': flavor1['id'],
                                           'doc_count': 1}]}
            }
        }

        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search/facets', is_admin=False
        )

        facets = self.plugin.get_facets(fake_request.context)
        self.assertTrue(list(filter(lambda f: f['name'] == 'name', facets)))
        self.assertFalse(
            list(filter(lambda f: f['name'].startswith('OS-EXT-SRV-ATTR'),
                        facets))
        )

        status_facet = list(filter(lambda f: f['name'] == 'status', facets))[0]
        expected_status = {
            'name': 'status',
            'options': [{'key': 'ACTIVE', 'doc_count': 2}],
            'type': 'string'
        }
        self.assertEqual(expected_status, status_facet)

        complex_facet_option_fields = (
            'image.id', 'flavor.id', 'networks.name',
            'networks.OS-EXT-IPS:type', 'networks.version',
            'security_groups.name')
        aggs = dict(unit_test_utils.complex_facet_field_agg(name)
                    for name in complex_facet_option_fields)

        simple_facet_option_fields = (
            'status', 'OS-EXT-AZ:availability_zone'
        )
        aggs.update(dict(unit_test_utils.simple_facet_field_agg(name)
                         for name in simple_facet_option_fields))

        expected_agg_query = {
            'aggs': aggs,
            'query': {
                'filtered': {
                    'filter': {
                        'and': [
                            {'term': {'tenant_id': TENANT1}}
                        ]
                    }
                }
            }
        }
        mock_engine.search.assert_called_with(
            index=self.plugin.get_index_name(),
            doc_type=self.plugin.get_document_type(),
            body=expected_agg_query,
            ignore_unavailable=True,
            search_type='count'
        )

    def test_facets_admin(self):
        mock_engine = mock.Mock()
        self.plugin.engine = mock_engine

        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search/facets', is_admin=True
        )

        mock_engine.search.return_value = {
            'aggregations': {
                'status': {
                    'buckets': [{'key': 'ACTIVE', 'doc_count': 2}]
                },
                'OS-EXT-AZ:availability_zone': {'buckets': []},
                'image.id': {'buckets': [{'key': imagea['id'],
                                          'doc_count': 1}]},
                'flavor.id': {'buckets': [{'key': flavor1['id'],
                                           'doc_count': 1}]},
                'security_groups': {'buckets': []},
                'network.name': {'buckets': []},
            }
        }

        facets = self.plugin.get_facets(fake_request.context)

        # Check created and updated fields aren't present, even for admins
        self.assertFalse(list(filter(lambda f: f['name'] == 'created',
                                     facets)))
        self.assertFalse(list(filter(lambda f: f['name'] == 'updated',
                                     facets)))
        self.assertTrue(list(filter(lambda f: f['name'] == 'created_at',
                                    facets)))
        self.assertTrue(list(filter(lambda f: f['name'] == 'updated_at',
                                    facets)))

        # Check unprotected fields are still present
        self.assertTrue(list(filter(lambda f: f['name'] == 'status', facets)))

        complex_facet_option_fields = (
            'image.id', 'flavor.id', 'networks.name',
            'networks.OS-EXT-IPS:type', 'networks.version',
            'security_groups.name')
        aggs = dict(unit_test_utils.complex_facet_field_agg(name)
                    for name in complex_facet_option_fields)

        simple_facet_option_fields = (
            'status', 'OS-EXT-AZ:availability_zone'
        )
        aggs.update(dict(unit_test_utils.simple_facet_field_agg(name)
                         for name in simple_facet_option_fields))

        expected_agg_query = {
            'aggs': aggs,
            'query': {
                'filtered': {
                    'filter': {
                        'and': [
                            {'term': {'tenant_id': TENANT1}}
                        ]
                    }
                }
            }
        }
        mock_engine.search.assert_called_with(
            index=self.plugin.get_index_name(),
            doc_type=self.plugin.get_document_type(),
            body=expected_agg_query,
            ignore_unavailable=True,
            search_type='count'
        )

    def test_facets_all_projects(self):
        # For non admins, all_projects should have no effect
        mock_engine = mock.Mock()
        self.plugin.engine = mock_engine

        # Don't really care about the return values
        mock_engine.search.return_value = {
            'aggregations': {}
        }

        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search/facets', is_admin=False
        )

        self.plugin.get_facets(fake_request.context, all_projects=True)

        complex_facet_option_fields = (
            'image.id', 'flavor.id', 'networks.name',
            'networks.OS-EXT-IPS:type', 'networks.version',
            'security_groups.name')
        aggs = dict(unit_test_utils.complex_facet_field_agg(name)
                    for name in complex_facet_option_fields)

        simple_facet_option_fields = ('status', 'OS-EXT-AZ:availability_zone')
        aggs.update(dict(unit_test_utils.simple_facet_field_agg(name)
                         for name in simple_facet_option_fields))

        expected_agg_query = {
            'aggs': aggs,
            'query': {
                'filtered': {
                    'filter': {
                        'and': [
                            {'term': {'tenant_id': TENANT1}}
                        ]
                    }
                }
            }
        }
        mock_engine.search.assert_called_with(
            index=self.plugin.get_index_name(),
            doc_type=self.plugin.get_document_type(),
            body=expected_agg_query,
            ignore_unavailable=True,
            search_type='count'
        )

        # Admins can request all_projects
        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search/facets', is_admin=True
        )

        self.plugin.get_facets(fake_request.context, all_projects=True)
        complex_facet_option_fields = (
            'image.id', 'flavor.id', 'networks.name',
            'networks.OS-EXT-IPS:type', 'networks.version',
            'security_groups.name')
        aggs = dict(unit_test_utils.complex_facet_field_agg(name)
                    for name in complex_facet_option_fields)
        simple_facet_option_fields = (
            'status', 'OS-EXT-AZ:availability_zone'
        )
        aggs.update(dict(unit_test_utils.simple_facet_field_agg(name)
                         for name in simple_facet_option_fields))

        # No query here
        expected_agg_query = {
            'aggs': aggs
        }
        mock_engine.search.assert_called_with(
            index=self.plugin.get_index_name(),
            doc_type=self.plugin.get_document_type(),
            body=expected_agg_query,
            ignore_unavailable=True,
            search_type='count'
        )

    def test_facets_no_mapping(self):
        mock_engine = mock.Mock()
        self.plugin.engine = mock_engine

        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search/facets', is_admin=True
        )

        mock_engine.search.return_value = {
            'aggregations': {
                'status': {'buckets': []},
                'image.id': {'doc_count': 0}
            }
        }

        facets = self.plugin.get_facets(fake_request.context)

        status_facet = list(filter(lambda f: f['name'] == 'status',
                                   facets))[0]
        image_facet = list(filter(lambda f: f['name'] == 'image.id',
                                  facets))[0]
        expected_status = {'name': 'status', 'options': [], 'type': 'string'}
        expected_image = {'name': 'image.id', 'options': [], 'type': 'string'}

        self.assertEqual(expected_status, status_facet)
        self.assertEqual(expected_image, image_facet)

    def test_created_at_updated_at(self):
        self.assertTrue('created_at' not in self.instance1.to_dict())
        self.assertTrue('updated_at' not in self.instance1.to_dict())

        with mock.patch(nova_server_getter, return_value=self.instance1):
            serialized = self.plugin.serialize(self.instance1.id)

        self.assertEqual(serialized['created_at'], created_now)
        self.assertEqual(serialized['updated_at'], updated_now)
