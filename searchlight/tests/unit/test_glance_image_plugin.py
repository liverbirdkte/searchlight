# Copyright 2015 Intel Corporation
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
import six

import glanceclient.exc
from oslo_utils import timeutils

from searchlight.elasticsearch.plugins.glance import images as images_plugin
import searchlight.tests.unit.utils as unit_test_utils
import searchlight.tests.utils as test_utils


DATETIME = datetime.datetime(2012, 5, 16, 15, 27, 36, 325355)
DATE1 = timeutils.isotime(DATETIME)

# General
USER1 = '54492ba0-f4df-4e4e-be62-27f4d76b29cf'

TENANT1 = '6838eb7b-6ded-434a-882c-b344c77fe8df'
TENANT2 = '2c014f32-55eb-467d-8fcb-4bd706012f81'
TENANT3 = '5a3e60e8-cfa9-4a9e-a90a-62b42cea92b8'
TENANT4 = 'c6c87f25-8a94-47ed-8c83-053c25f42df4'

# Images
UUID1 = 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d'
UUID2 = 'a85abd86-55b3-4d5b-b0b4-5d0a6e6042fc'
UUID3 = '971ec09a-8067-4bc8-a91f-ae3557f1c4c7'
UUID4 = '6bbe7cc2-eae7-4c0f-b50d-a7160b0c6a86'
UUID5 = 'KERNEL-eae7-4c0f-b50d-RAMDISK'

CHECKSUM = '93264c3edf5972c9f1cb309543d38a5c'


def _image_fixture(image_id, **kwargs):
    """Simulates a v2 image (which is just a dictionary)
    """
    extra_properties = kwargs.pop('extra_properties', {})

    image = {
        'id': image_id,
        'name': None,
        'visibility': 'public',
        'kernel_id': None,
        'file': 'v2/images/' + image_id,
        'checksum': None,
        'owner': None,
        'status': 'queued',
        'tags': [],
        'size': None,
        'virtual_size': None,
        'locations': [],
        'protected': False,
        'disk_format': None,
        'container_format': None,
        'min_ram': None,
        'min_disk': None,
        'created_at': DATE1,
        'updated_at': DATE1,
    }
    image.update(kwargs)
    for k, v in six.iteritems(extra_properties):
        image[k] = v
    return image


def _notification_fixture(image_id, **kwargs):
    properties = kwargs.pop('properties', {})
    notification = {
        'id': image_id,
        'name': None,
        'status': 'active',
        'virtual_size': None,
        'deleted': False,
        'disk_format': None,
        'container_format': None,
        'min_ram': None,
        'min_disk': None,
        'protected': False,
        'checksum': None,
        'owner': None,
        'is_public': True,
        'deleted_at': None,
        'size': None,
        'created_at': DATE1,
        'updated_at': DATE1,
        'properties': {}
    }
    for k, v in six.iteritems(kwargs):
        if k in notification:
            notification[k] = v
    for k, v in six.iteritems(properties):
        notification['properties'][k] = v
    return notification


class TestImageLoaderPlugin(test_utils.BaseTestCase):
    def setUp(self):
        super(TestImageLoaderPlugin, self).setUp()
        self.set_property_protections()

        self._create_images()

        self.plugin = images_plugin.ImageIndex()
        self.notification_handler = self.plugin.get_notification_handler()

        self.mock_session = mock.Mock()
        self.mock_session.get_endpoint.return_value = \
            'http://localhost/glance/v2'
        patched_ses = mock.patch(
            'searchlight.elasticsearch.plugins.openstack_clients._get_session',
            return_value=self.mock_session)
        patched_ses.start()
        self.addCleanup(patched_ses.stop)

    def _create_images(self):
        self.simple_image = _image_fixture(
            UUID1, owner=TENANT1, checksum=CHECKSUM, name='simple', size=256,
            visibility='public', status='active'
        )
        self.tagged_image = _image_fixture(
            UUID2, owner=TENANT1, checksum=CHECKSUM, name='tagged', size=512,
            visibility='public', status='active', tags=['ping', 'pong'],
        )
        self.complex_image = _image_fixture(
            UUID3, owner=TENANT2, checksum=CHECKSUM, name='complex', size=256,
            visibility='public', status='active',
            extra_properties={'mysql_version': '5.6', 'hypervisor': 'lxc'}
        )
        self.members_image = _image_fixture(
            UUID3, owner=TENANT2, checksum=CHECKSUM, name='complex', size=256,
            visibility='private', status='active',
        )
        self.members_image_members = [
            {'member_id': TENANT1, 'status': 'accepted'},
            {'member_id': TENANT2, 'status': 'accepted'},
            {'member_id': TENANT3, 'status': 'accepted'},
            {'member_id': TENANT4, 'status': 'pending'},
        ]
        self.kernel_ramdisk_image = _image_fixture(
            UUID5, owner=TENANT1, checksum=CHECKSUM, name='kernel_ramdisk',
            size=256, visibility='public', status='active',
            kernel_id='KERNEL-ID-SEARCH-LIGHT-ROCKS',
            ramdisk_id='RAMDISK-ID-GO-BRONCOS',
        )
        self.images = [self.simple_image, self.tagged_image,
                       self.complex_image, self.members_image,
                       self.kernel_ramdisk_image]

    def test_index_name(self):
        self.assertEqual('searchlight', self.plugin.get_index_name())

    def test_document_type(self):
        self.assertEqual('OS::Glance::Image', self.plugin.get_document_type())

    # This test can be removed once we can use glanceclient>=1.0
    def test_glanceclient_unauthorized(self):
        with mock.patch('glanceclient.v2.image_members.Controller.list',
                        side_effect=[glanceclient.exc.Unauthorized,
                                     self.members_image_members]) as mock_mem:
            self.plugin.serialize(self.members_image)
            self.assertEqual(2, mock_mem.call_count)

    def test_image_serialize(self):
        expected = {
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'container_format': None,
            'disk_format': None,
            'id': 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d',
            'kernel_id': None,
            'members': [],
            'min_disk': None,
            'min_ram': None,
            'name': 'simple',
            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
            'protected': False,
            'size': 256,
            'status': 'active',
            'tags': [],
            'virtual_size': None,
            'visibility': 'public',
            'created_at': DATE1,
            'updated_at': DATE1
        }
        serialized = self.plugin.serialize(self.simple_image)
        self.assertEqual(expected, serialized)

    def test_image_with_tags_serialize(self):
        expected = {
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'container_format': None,
            'disk_format': None,
            'id': 'a85abd86-55b3-4d5b-b0b4-5d0a6e6042fc',
            'kernel_id': None,
            'members': [],
            'min_disk': None,
            'min_ram': None,
            'name': 'tagged',
            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
            'protected': False,
            'size': 512,
            'status': 'active',
            'tags': ['ping', 'pong'],
            'virtual_size': None,
            'visibility': 'public',
            'created_at': DATE1,
            'updated_at': DATE1
        }
        serialized = self.plugin.serialize(self.tagged_image)
        self.assertEqual(expected, serialized)

    def test_image_with_properties_serialize(self):
        expected = {
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'container_format': None,
            'disk_format': None,
            'hypervisor': 'lxc',
            'id': '971ec09a-8067-4bc8-a91f-ae3557f1c4c7',
            'kernel_id': None,
            'members': [],
            'min_disk': None,
            'min_ram': None,
            'mysql_version': '5.6',
            'name': 'complex',
            'owner': '2c014f32-55eb-467d-8fcb-4bd706012f81',
            'protected': False,
            'size': 256,
            'status': 'active',
            'tags': [],
            'virtual_size': None,
            'visibility': 'public',
            'created_at': DATE1,
            'updated_at': DATE1
        }

        serialized = self.plugin.serialize(self.complex_image)
        self.assertEqual(expected, serialized)

    def test_image_with_members_serialize(self):
        expected = {
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'container_format': None,
            'disk_format': None,
            'id': '971ec09a-8067-4bc8-a91f-ae3557f1c4c7',
            'kernel_id': None,
            'members': ['6838eb7b-6ded-434a-882c-b344c77fe8df',
                        '2c014f32-55eb-467d-8fcb-4bd706012f81',
                        '5a3e60e8-cfa9-4a9e-a90a-62b42cea92b8'],
            'min_disk': None,
            'min_ram': None,
            'name': 'complex',
            'owner': '2c014f32-55eb-467d-8fcb-4bd706012f81',
            'protected': False,
            'size': 256,
            'status': 'active',
            'tags': [],
            'virtual_size': None,
            'visibility': 'private',
            'created_at': DATE1,
            'updated_at': DATE1
        }

        with mock.patch('glanceclient.v2.image_members.Controller.list',
                        return_value=self.members_image_members):
            serialized = self.plugin.serialize(self.members_image)
        self.assertEqual(expected, serialized)

    def test_image_kernel_ramdisk_serialize(self):
        expected = {
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'container_format': None,
            'disk_format': None,
            'id': UUID5,
            'kernel_id': 'KERNEL-ID-SEARCH-LIGHT-ROCKS',
            'ramdisk_id': 'RAMDISK-ID-GO-BRONCOS',
            'members': [],
            'min_disk': None,
            'min_ram': None,
            'name': 'kernel_ramdisk',
            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
            'protected': False,
            'size': 256,
            'status': 'active',
            'tags': [],
            'virtual_size': None,
            'visibility': 'public',
            'created_at': DATE1,
            'updated_at': DATE1
        }
        serialized = self.plugin.serialize(self.kernel_ramdisk_image)
        self.assertEqual(expected, serialized)

    def test_setup_data(self):
        """Tests initial data load."""
        image_member_mocks = [
            self.members_image_members
        ]
        with mock.patch('glanceclient.v2.images.Controller.list',
                        return_value=self.images) as mock_list:
            with mock.patch('glanceclient.v2.image_members.Controller.list',
                            side_effect=image_member_mocks) as mock_members:
                # This is not testing the elasticsearch call, just
                # that the documents being indexed are as expected
                with mock.patch.object(
                        self.plugin,
                        'save_documents') as mock_save:
                    self.plugin.setup_data()

                    mock_list.assert_called_once_with()
                    mock_members.assert_called_once_with(
                        self.members_image['id'])

                    mock_save.assert_called_once_with([
                        {
                            'kernel_id': None,
                            'tags': [],
                            'protected': False,
                            'min_disk': None,
                            'min_ram': None,
                            'virtual_size': None,
                            'size': 256,
                            'container_format': None,
                            'status': 'active',
                            'updated_at': '2012-05-16T15:27:36Z',
                            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
                            'members': [],
                            'visibility': 'public',
                            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
                            'disk_format': None,
                            'name': 'simple',
                            'created_at': '2012-05-16T15:27:36Z',
                            'id': 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d'
                        },
                        {
                            'kernel_id': None,
                            'tags': ['ping', 'pong'],
                            'protected': False,
                            'min_disk': None,
                            'min_ram': None,
                            'virtual_size': None,
                            'size': 512,
                            'container_format': None,
                            'status': 'active',
                            'updated_at': '2012-05-16T15:27:36Z',
                            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
                            'members': [],
                            'visibility': 'public',
                            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
                            'disk_format': None,
                            'name': 'tagged',
                            'created_at': '2012-05-16T15:27:36Z',
                            'id': 'a85abd86-55b3-4d5b-b0b4-5d0a6e6042fc'},
                        {
                            'kernel_id': None,
                            'tags': [], 'protected': False,
                            'min_disk': None,
                            'min_ram': None,
                            'virtual_size': None,
                            'size': 256,
                            'container_format': None,
                            'status': 'active',
                            'updated_at': '2012-05-16T15:27:36Z',
                            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
                            'members': [],
                            'mysql_version': '5.6',
                            'visibility': 'public',
                            'hypervisor': 'lxc',
                            'owner': '2c014f32-55eb-467d-8fcb-4bd706012f81',
                            'id': '971ec09a-8067-4bc8-a91f-ae3557f1c4c7',
                            'name': 'complex',
                            'created_at': '2012-05-16T15:27:36Z',
                            'disk_format': None
                        },
                        {
                            'kernel_id': None, 'tags': [],
                            'protected': False,
                            'min_disk': None,
                            'min_ram': None,
                            'virtual_size': None,
                            'size': 256,
                            'container_format': None,
                            'status': 'active',
                            'updated_at': '2012-05-16T15:27:36Z',
                            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
                            'members': [
                                '6838eb7b-6ded-434a-882c-b344c77fe8df',
                                '2c014f32-55eb-467d-8fcb-4bd706012f81',
                                '5a3e60e8-cfa9-4a9e-a90a-62b42cea92b8'
                            ],
                            'visibility': 'private',
                            'owner': '2c014f32-55eb-467d-8fcb-4bd706012f81',
                            'disk_format': None,
                            'name': 'complex',
                            'created_at': '2012-05-16T15:27:36Z',
                            'id': '971ec09a-8067-4bc8-a91f-ae3557f1c4c7'
                        },
                        {
                            'kernel_id': 'KERNEL-ID-SEARCH-LIGHT-ROCKS',
                            'tags': [], 'protected': False,
                            'min_disk': None,
                            'ramdisk_id': 'RAMDISK-ID-GO-BRONCOS',
                            'min_ram': None,
                            'virtual_size': None,
                            'size': 256,
                            'container_format': None,
                            'status': 'active',
                            'updated_at': '2012-05-16T15:27:36Z',
                            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
                            'members': [],
                            'visibility': 'public',
                            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
                            'disk_format': None,
                            'name': 'kernel_ramdisk',
                            'created_at': '2012-05-16T15:27:36Z',
                            'id': 'KERNEL-eae7-4c0f-b50d-RAMDISK'
                        }
                    ])

    def test_image_rbac(self):
        """Test the image plugin RBAC query terms"""
        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search'
        )
        rbac_query_fragment = self.plugin.get_rbac_filter(fake_request.context)
        expected_fragment = [{
            "indices": {
                "index": "searchlight",
                "no_match_filter": "none",
                "filter": {
                    "and": [
                        {
                            "or": [
                                {"term": {"owner": TENANT1}},
                                {"term": {"visibility": "public"}},
                                {"term": {"members": TENANT1}}
                            ]
                        },
                        {
                            "type": {"value": "OS::Glance::Image"}
                        },
                    ]
                },
            }
        }]

        self.assertEqual(expected_fragment, rbac_query_fragment)

    def test_protected_properties(self):
        extra_props = {
            'x_foo_matcher': 'this is protected',
            'x_foo_something_else': 'this is not protected',
            'z_this_has_no_rules': 'this is protected too'
        }
        image_with_properties = _image_fixture(
            UUID1, owner=TENANT1, checksum=CHECKSUM, name='simple', size=256,
            status='active', extra_properties=extra_props
        )

        with mock.patch('glanceclient.v2.image_members.Controller.list',
                        return_value=[]):
            serialized = self.plugin.serialize(image_with_properties)

        elasticsearch_results = {
            'hits': {
                'hits': [{
                    '_source': copy.deepcopy(serialized),
                    '_type': self.plugin.get_document_type(),
                    '_index': self.plugin.get_index_name()
                }]
            }
        }

        # Admin context
        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search', is_admin=True
        )

        for result_hit in elasticsearch_results['hits']['hits']:
            self.plugin.filter_result(result_hit, fake_request.context)

        # This should contain the three properties we added
        expected = {
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'container_format': None,
            'disk_format': None,
            'id': 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d',
            'kernel_id': None,
            'members': [],
            'min_disk': None,
            'min_ram': None,
            'name': 'simple',
            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
            'protected': False,
            'size': 256,
            'status': 'active',
            'tags': [],
            'virtual_size': None,
            'visibility': 'public',
            'created_at': DATE1,
            'updated_at': DATE1,
            'x_foo_matcher': 'this is protected',
            'x_foo_something_else': 'this is not protected',
            'z_this_has_no_rules': 'this is protected too'
        }

        self.assertEqual(expected,
                         elasticsearch_results['hits']['hits'][0]['_source'])

        # Non admin user. Recreate this because the filter operation modifies
        # it in place and we want a fresh copy
        elasticsearch_results = {
            'hits': {
                'hits': [{
                    '_source': copy.deepcopy(serialized),
                    '_type': self.plugin.get_document_type(),
                    '_index': self.plugin.get_index_name()
                }]
            }
        }
        # Non admin context should miss the x_foo property
        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search', is_admin=False
        )

        for result_hit in elasticsearch_results['hits']['hits']:
            self.plugin.filter_result(result_hit, fake_request.context)

        # Should be missing two of the properties
        expected = {
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'container_format': None,
            'disk_format': None,
            'id': 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d',
            'members': [],
            'min_disk': None,
            'min_ram': None,
            'name': 'simple',
            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
            'protected': False,
            'size': 256,
            'status': 'active',
            'tags': [],
            'virtual_size': None,
            'visibility': 'public',
            'created_at': DATE1,
            'updated_at': DATE1,
            'x_foo_something_else': 'this is not protected'
        }

        self.assertEqual(expected,
                         elasticsearch_results['hits']['hits'][0]['_source'])

    def test_image_notification_serialize(self):
        notification = _notification_fixture(
            self.simple_image['id'],
            checksum=self.simple_image['checksum'],
            name=self.simple_image['name'],
            is_public=True,
            size=self.simple_image['size'],
            properties={'prop1': 'val1'},
            owner=self.simple_image['owner'])

        expected = {
            'status': 'active',
            # Tags are not contained in notifications
            # 'tags': [],
            'container_format': None,
            'min_ram': None,
            'visibility': 'public',
            'owner': '6838eb7b-6ded-434a-882c-b344c77fe8df',
            'min_disk': None,
            'members': [],
            'virtual_size': None,
            'id': 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d',
            'size': 256,
            'prop1': 'val1',
            'name': 'simple',
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'disk_format': None,
            'protected': False,
            'created_at': DATE1,
            'updated_at': DATE1
        }

        serialized = self.notification_handler.serialize_notification(
            notification)
        self.assertEqual(expected, serialized)

    def test_private_image_notification_serialize(self):
        """Test a notification for a private image"""
        notification = _notification_fixture(
            self.members_image['id'],
            checksum=self.members_image['checksum'],
            name=self.members_image['name'],
            is_public=False,
            size=self.members_image['size'],
            owner=self.members_image['owner'])

        expected = {
            'status': 'active',
            # Tags are not contained in notifications
            # 'tags': [],
            'container_format': None,
            'min_ram': None,
            'visibility': 'private',
            'owner': '2c014f32-55eb-467d-8fcb-4bd706012f81',
            'members': [
                '6838eb7b-6ded-434a-882c-b344c77fe8df',
                '2c014f32-55eb-467d-8fcb-4bd706012f81',
                '5a3e60e8-cfa9-4a9e-a90a-62b42cea92b8'
            ],
            'min_disk': None,
            'virtual_size': None,
            'id': '971ec09a-8067-4bc8-a91f-ae3557f1c4c7',
            'size': 256,
            'name': 'complex',
            'checksum': '93264c3edf5972c9f1cb309543d38a5c',
            'disk_format': None,
            'protected': False,
            'created_at': DATE1,
            'updated_at': DATE1
        }
        with mock.patch('glanceclient.v2.image_members.Controller.list',
                        return_value=self.members_image_members):
            serialized = self.notification_handler.serialize_notification(
                notification)
        self.assertEqual(expected, serialized)

    def test_facets(self):
        # Nova tests are more thorough; checking that the right fields are
        # faceted
        mock_engine = mock.Mock()
        self.plugin.engine = mock_engine

        fake_request = unit_test_utils.get_fake_request(
            USER1, TENANT1, '/v1/search/facets', is_admin=False
        )

        mock_engine.search.return_value = {
            'aggregations': {
                'container_format': {'buckets': []},
                'disk_format': {'buckets': [{'key': 'raw', 'doc_count': 3}]},
                'tags': {'buckets': []},
                'status': {'buckets': []},
                'visibility': {'buckets': []},
                'protected': {'buckets': []}
            }
        }

        facets = self.plugin.get_facets(fake_request.context)

        disk_format_facets = list(filter(lambda f: f['name'] == 'disk_format',
                                         facets))[0]
        expected_disk_format_facet = {
            'name': 'disk_format',
            'options': [{'key': 'raw', 'doc_count': 3}],
            'type': 'string'
        }
        self.assertEqual(expected_disk_format_facet, disk_format_facets)

        facet_option_fields = ('disk_format', 'container_format', 'tags',
                               'visibility', 'status', 'protected')
        expected_agg_query = {
            'aggs': dict(unit_test_utils.simple_facet_field_agg(name)
                         for name in facet_option_fields),
            'query': {
                'filtered': {
                    'filter': {
                        'and': [
                            {
                                "or": [
                                    {'term': {'owner': TENANT1}},
                                    {'term': {'visibility': 'public'}},
                                    {'term': {'members': TENANT1}}
                                ]
                            }
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
