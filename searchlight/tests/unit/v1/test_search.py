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

import mock
from oslo_serialization import jsonutils
import six
import webob.exc

from searchlight.api.v1 import search as search
from searchlight.common import exception
from searchlight.common import utils
import searchlight.elasticsearch
import searchlight.gateway
import searchlight.tests.unit.utils as unit_test_utils
import searchlight.tests.utils as test_utils


def _action_fixture(op_type, data, index=None, doc_type=None, _id=None,
                    **kwargs):
    action = {
        'action': op_type,
        'id': _id,
        'index': index,
        'type': doc_type,
        'data': data,
    }
    if kwargs:
        action.update(kwargs)

    return action


def _image_fixture(op_type, _id=None, index='searchlight',
                   doc_type='OS::Glance::Image',
                   data=None, **kwargs):
    image_data = {
        'name': 'image-1',
        'disk_format': 'raw',
    }
    if data is not None:
        image_data.update(data)

    return _action_fixture(op_type, image_data, index, doc_type, _id, **kwargs)


class TestControllerIndex(test_utils.BaseTestCase):
    def setUp(self):
        super(TestControllerIndex, self).setUp()
        self.search_controller = search.SearchController()

    def test_index_complete(self):
        request = unit_test_utils.get_fake_request(is_admin=True)
        self.search_controller.index = mock.Mock(return_value="{}")
        actions = [{'action': 'create', 'index': 'myindex', 'id': 10,
                    'type': 'MyTest', 'data': '{"name": "MyName"}'}]
        default_index = 'searchlight'
        default_type = 'OS::Glance::Image'

        self.search_controller.index(
            request, actions, default_index, default_type)
        self.search_controller.index.assert_called_once_with(
            request, actions, default_index, default_type)

    def test_index_repo_complete(self):
        request = unit_test_utils.get_fake_request(is_admin=True)
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.index = mock.Mock(return_value="{}")
        actions = [{'action': 'create', 'index': 'myindex', 'id': 10,
                    'type': 'MyTest', 'data': '{"name": "MyName"}'}]
        default_index = 'searchlight'
        default_type = 'OS::Glance::Image'

        self.search_controller.index(
            request, actions, default_index, default_type)
        repo.index.assert_called_once_with(
            default_index, default_type, actions)

    def test_index_repo_minimal(self):
        request = unit_test_utils.get_fake_request(is_admin=True)
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.index = mock.Mock(return_value="{}")
        actions = [{'action': 'create', 'index': 'myindex', 'id': 10,
                    'type': 'MyTest', 'data': '{"name": "MyName"}'}]

        self.search_controller.index(request, actions)
        repo.index.assert_called_once_with(None, None, actions)

    def test_index_forbidden(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.index = mock.Mock(side_effect=exception.Forbidden)
        actions = [{'action': 'create', 'index': 'myindex', 'id': 10,
                    'type': 'MyTest', 'data': '{"name": "MyName"}'}]

        self.assertRaises(
            webob.exc.HTTPForbidden, self.search_controller.index,
            request, actions)

    def test_index_not_found(self):
        request = unit_test_utils.get_fake_request(is_admin=True)
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.index = mock.Mock(side_effect=exception.NotFound)
        actions = [{'action': 'create', 'index': 'myindex', 'id': 10,
                    'type': 'MyTest', 'data': '{"name": "MyName"}'}]

        self.assertRaises(
            webob.exc.HTTPNotFound, self.search_controller.index,
            request, actions)

    def test_index_duplicate(self):
        request = unit_test_utils.get_fake_request(is_admin=True)
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.index = mock.Mock(side_effect=exception.Duplicate)
        actions = [{'action': 'create', 'index': 'myindex', 'id': 10,
                    'type': 'MyTest', 'data': '{"name": "MyName"}'}]

        self.assertRaises(
            webob.exc.HTTPConflict, self.search_controller.index,
            request, actions)

    def test_index_exception(self):
        request = unit_test_utils.get_fake_request(is_admin=True)
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.index = mock.Mock(side_effect=Exception)
        actions = [{'action': 'create', 'index': 'myindex', 'id': 10,
                    'type': 'MyTest', 'data': '{"name": "MyName"}'}]

        self.assertRaises(
            webob.exc.HTTPInternalServerError, self.search_controller.index,
            request, actions)


class TestControllerSearch(test_utils.BaseTestCase):

    def setUp(self):
        super(TestControllerSearch, self).setUp()
        self.search_controller = search.SearchController()

    def test_search_all(self):
        request = unit_test_utils.get_fake_request()
        self.search_controller.search = mock.Mock(return_value="{}")

        query = {"match_all": {}}
        index_name = "searchlight"
        doc_type = "OS::Glance::Metadef"
        offset = 0
        limit = 10
        self.search_controller.search(
            request, query, index_name, doc_type, offset, limit)
        self.search_controller.search.assert_called_once_with(
            request, query, index_name, doc_type, offset, limit)

    def test_search_all_repo(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.search = mock.Mock(return_value={})
        query = {"match_all": {}}
        index_name = "searchlight"
        doc_type = "OS::Glance::Metadef"
        offset = 0
        limit = 10
        self.search_controller.search(
            request, query, index_name, doc_type, offset, limit)
        repo.search.assert_called_once_with(
            index_name, doc_type, query, offset,
            limit, ignore_unavailable=True)

    def test_search_forbidden(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.search = mock.Mock(side_effect=exception.Forbidden)

        query = {"match_all": {}}
        index_name = "searchlight"
        doc_type = "OS::Glance::Metadef"
        offset = 0
        limit = 10

        self.assertRaises(
            webob.exc.HTTPForbidden, self.search_controller.search,
            request, query, index_name, doc_type, offset, limit)

    def test_search_not_found(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.search = mock.Mock(side_effect=exception.NotFound)

        query = {"match_all": {}}
        index_name = "searchlight"
        doc_type = "OS::Glance::Metadef"
        offset = 0
        limit = 10

        self.assertRaises(
            webob.exc.HTTPNotFound, self.search_controller.search, request,
            query, index_name, doc_type, offset, limit)

    def test_search_duplicate(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.search = mock.Mock(side_effect=exception.Duplicate)

        query = {"match_all": {}}
        index_name = "searchlight"
        doc_type = "OS::Glance::Metadef"
        offset = 0
        limit = 10

        self.assertRaises(
            webob.exc.HTTPConflict, self.search_controller.search, request,
            query, index_name, doc_type, offset, limit)

    def test_search_internal_server_error(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.search = mock.Mock(side_effect=Exception)

        query = {"match_all": {}}
        index_name = "searchlight"
        doc_type = "OS::Glance::Metadef"
        offset = 0
        limit = 10

        self.assertRaises(
            webob.exc.HTTPInternalServerError, self.search_controller.search,
            request, query, index_name, doc_type, offset, limit)


class TestControllerPluginsInfo(test_utils.BaseTestCase):

    def setUp(self):
        super(TestControllerPluginsInfo, self).setUp()
        self.search_controller = search.SearchController()

    def test_plugins_info_forbidden(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.plugins_info = mock.Mock(side_effect=exception.Forbidden)

        self.assertRaises(
            webob.exc.HTTPForbidden, self.search_controller.plugins_info,
            request)

    def test_plugins_info_not_found(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.plugins_info = mock.Mock(side_effect=exception.NotFound)

        self.assertRaises(webob.exc.HTTPNotFound,
                          self.search_controller.plugins_info, request)

    def test_plugins_info_internal_server_error(self):
        request = unit_test_utils.get_fake_request()
        repo = searchlight.elasticsearch.CatalogSearchRepo
        repo.plugins_info = mock.Mock(side_effect=Exception)

        self.assertRaises(webob.exc.HTTPInternalServerError,
                          self.search_controller.plugins_info, request)

    def test_plugins_info(self):
        request = unit_test_utils.get_fake_request()
        expected = {
            "plugins": [
                {
                    "index": "searchlight",
                    "type": "OS::Designate::RecordSet",
                    "name": "OS::Designate::RecordSet"
                },
                {
                    "index": "searchlight",
                    "type": "OS::Designate::Zone",
                    "name": "OS::Designate::Zone"
                },
                {
                    "index": "searchlight", "type": "OS::Glance::Image",
                    "name": "OS::Glance::Image"
                },
                {
                    "index": "searchlight", "type": "OS::Glance::Metadef",
                    "name": "OS::Glance::Metadef"
                },
                {
                    "index": "searchlight", "type": "OS::Nova::Server",
                    "name": "OS::Nova::Server"
                }
            ]
        }

        actual = self.search_controller.plugins_info(request)
        self.assertEqual(sorted(expected), sorted(actual))


class TestSearchDeserializer(test_utils.BaseTestCase):

    def setUp(self):
        super(TestSearchDeserializer, self).setUp()
        self.deserializer = search.RequestDeserializer(
            utils.get_search_plugins()
        )

    def test_single_index(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'index': 'searchlight',
        }))

        output = self.deserializer.search(request)
        self.assertEqual(['searchlight'], output['index'])

    def test_single_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': 'OS::Glance::Image',
        }))

        output = self.deserializer.search(request)
        self.assertEqual(['searchlight'], output['index'])
        self.assertEqual(['OS::Glance::Image'], output['doc_type'])

    def test_empty_request(self):
        """Tests that ALL registered resource types are searched"""
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({}))

        output = self.deserializer.search(request)
        self.assertEqual(['searchlight'], output['index'])

        types = [
            'OS::Designate::RecordSet',
            'OS::Designate::Zone',
            'OS::Glance::Image',
            'OS::Glance::Metadef',
            'OS::Nova::Server',
        ]

        self.assertEqual(['searchlight'], output['index'])
        self.assertEqual(sorted(types), sorted(output['doc_type']))

    def test_empty_request_admin(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({}))
        request.context.is_admin = True

        output = self.deserializer.search(request)
        types = [
            'OS::Designate::RecordSet',
            'OS::Designate::Zone',
            'OS::Glance::Image',
            'OS::Glance::Metadef',
            'OS::Nova::Server'
        ]
        self.assertEqual(['searchlight'], output['index'])
        self.assertEqual(sorted(types), sorted(output['doc_type']))

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'index': 'invalid',
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_invalid_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': 'invalid',
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_forbidden_schema(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'schema': {},
        }))

        self.assertRaises(webob.exc.HTTPForbidden, self.deserializer.search,
                          request)

    def test_forbidden_self(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'self': {},
        }))

        self.assertRaises(webob.exc.HTTPForbidden, self.deserializer.search,
                          request)

    def test_fields_restriction(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            '_source': ['description'],
        }))

        output = self.deserializer.search(request)
        self.assertEqual(['searchlight'], output['index'])
        self.assertEqual(['OS::Glance::Metadef'], output['doc_type'])
        self.assertEqual(['description'], output['_source'])

    def test_fields_include_exclude(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            '_source': {
                'include': ['some', 'thing.*'],
                'exclude': ['other.*', 'thing']
            }
        }))

        output = self.deserializer.search(request)
        self.assertFalse('_source' in output)
        self.assertEqual(['some', 'thing.*'], output['_source_include'])
        self.assertEqual(['other.*', 'thing'], output['_source_exclude'])

    def test_bad_field_include(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            '_source': 1234,
        }))

        self.assertRaisesRegexp(
            webob.exc.HTTPBadRequest,
            "'_source' must be a string, dict or list",
            self.deserializer.search,
            request)

    def test_highlight_fields(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            'highlight': {'fields': {'name': {}}}
        }))

        output = self.deserializer.search(request)
        self.assertEqual(['searchlight'], output['index'])
        self.assertEqual(['OS::Glance::Metadef'], output['doc_type'])
        self.assertEqual({'name': {}}, output['query']['highlight']['fields'])

    def test_invalid_limit(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            'limit': 'invalid',
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.search,
                          request)

    def test_negative_limit(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            'limit': -1,
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.search,
                          request)

    def test_invalid_offset(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            'offset': 'invalid',
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.search,
                          request)

    def test_negative_offset(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            'offset': -1,
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.search,
                          request)

    def test_limit_and_offset(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'type': ['OS::Glance::Metadef'],
            'query': {'match_all': {}},
            'limit': 1,
            'offset': 2,
        }))

        output = self.deserializer.search(request)
        self.assertEqual(['searchlight'], output['index'])
        self.assertEqual(['OS::Glance::Metadef'], output['doc_type'])
        self.assertEqual(1, output['limit'])
        self.assertEqual(2, output['offset'])

    def test_single_sort(self):
        """Test that a single sort field is correctly transformed"""
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
            'sort': 'status'
        }))

        output = self.deserializer.search(request)
        self.assertEqual(['status'], output['query']['sort'])

    def test_single_sort_dir(self):
        """Test that a single sort field & dir is correctly transformed"""
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
            'sort': {'status': 'desc'}
        }))

        output = self.deserializer.search(request)
        self.assertEqual([{'status': 'desc'}], output['query']['sort'])

    def test_multiple_sort(self):
        """Test multiple sort fields"""
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
            'sort': [
                'status',
                {'created_at': 'desc'},
                {'members': {'order': 'asc', 'mode': 'max'}}
            ]
        }))

        output = self.deserializer.search(request)
        expected = [
            'status',
            {'created_at': 'desc'},
            {'members': {'order': 'asc', 'mode': 'max'}}
        ]
        self.assertEqual(expected, output['query']['sort'])

    def test_raw_field_sort(self):
        """Some fields (like name) are treated separately"""
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
            'sort': [
                'name',
                {'name': {'order': 'desc'}}
            ]
        }))

        output = self.deserializer.search(request)
        expected = [
            'name.raw',
            {'name.raw': {'order': 'desc'}}
        ]
        self.assertEqual(expected, output['query']['sort'])

    def test_bad_sort(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'index': ['glance'],
            'type': ['OS::Glance::Image'],
            'query': {'match_all': {}},
            'sort': 1234
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.search,
                          request)

    @mock.patch('searchlight.elasticsearch.plugins.nova.servers.' +
                'ServerIndex.get_rbac_filter')
    def test_rbac_exception(self, mock_rbac_filter):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
        }))

        mock_rbac_filter.side_effect = Exception("Bad RBAC")

        self.assertRaisesRegexp(
            webob.exc.HTTPInternalServerError,
            "Error processing OS::Nova::Server RBAC filter",
            self.deserializer.search,
            request)

    def test_rbac_non_admin(self):
        """Test that a non-admin request results in an RBACed query"""
        request = unit_test_utils.get_fake_request(is_admin=False)
        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
            'type': 'OS::Nova::Server',
        }))
        output = self.deserializer.search(request)

        nova_rbac_filter = {
            'indices': {
                'filter': {
                    'and': [{
                        'term': {
                            'tenant_id': '6838eb7b-6ded-dead-beef-b344c77fe8df'
                        }},
                        {'type': {'value': 'OS::Nova::Server'}}
                    ]},
                'index': 'searchlight',
                'no_match_filter': 'none'
            }
        }

        expected_query = {
            'query': {
                'bool': {
                    'should': [{
                        'filtered': {
                            'filter': [nova_rbac_filter],
                            'query': {u'match_all': {}}
                        }
                    }]
                }
            }
        }

        self.assertEqual(expected_query, output['query'])

    def test_rbac_admin(self):
        """Test that admins have RBAC applied unless 'all_projects' is true"""
        request = unit_test_utils.get_fake_request(is_admin=True)
        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
            'type': 'OS::Nova::Server',
        }))
        output = self.deserializer.search(request)

        nova_rbac_filter = {
            'indices': {
                'filter': {
                    'and': [{
                        'term': {
                            'tenant_id': '6838eb7b-6ded-dead-beef-b344c77fe8df'
                        }},
                        {'type': {'value': 'OS::Nova::Server'}}
                    ]},
                'index': 'searchlight',
                'no_match_filter': 'none'
            }
        }
        expected_query = {
            'query': {
                'bool': {
                    'should': [{
                        'filtered': {
                            'filter': [nova_rbac_filter],
                            'query': {u'match_all': {}}
                        }
                    }]
                }
            }
        }

        self.assertEqual(expected_query, output['query'])

        request.body = six.b(jsonutils.dumps({
            'query': {'match_all': {}},
            'type': 'OS::Nova::Server',
            'all_projects': True,
        }))
        output = self.deserializer.search(request)

        expected_query = {
            'query': {'match_all': {}},
        }
        self.assertEqual(expected_query, output['query'])

    def test_default_facet_options(self):
        request = unit_test_utils.get_fake_request(path='/v1/search/facets')
        output = self.deserializer.facets(request)

        expected = {'index_name': None, 'doc_type': None,
                    'all_projects': False, 'limit_terms': 0}
        self.assertEqual(expected, output)


class TestIndexDeserializer(test_utils.BaseTestCase):
    def setUp(self):
        super(TestIndexDeserializer, self).setUp()
        self.deserializer = search.RequestDeserializer(
            utils.get_search_plugins()
        )

    def test_empty_request(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({}))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_empty_actions(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'default_type': 'OS::Glance::Image',
            'actions': [],
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_missing_actions(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'default_type': 'OS::Glance::Image'
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_invalid_operation_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('invalid', '1')]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_invalid_default_index(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'default_index': 'invalid',
            'actions': [_image_fixture('create', '1')]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_invalid_default_doc_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'default_type': 'invalid',
            'actions': [_image_fixture('create', '1')]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_empty_operation_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('', '1')]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_missing_operation_type(self):
        action = _image_fixture('', '1')
        action.pop('action')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': 'searchlight',
                '_op_type': 'index',
                '_source': {'disk_format': 'raw', 'name': 'image-1'},
                '_type': 'OS::Glance::Image'
            }],
            'default_index': None,
            'default_type': None
        }
        self.assertEqual(expected, output)

    def test_create_single(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('create', '1')]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': 'searchlight',
                '_op_type': 'create',
                '_source': {'disk_format': 'raw', 'name': 'image-1'},
                '_type': 'OS::Glance::Image'
            }],
            'default_index': None,
            'default_type': None
        }
        self.assertEqual(expected, output)

    def test_create_multiple(self):
        actions = [
            _image_fixture('create', '1'),
            _image_fixture('create', '2', data={'name': 'image-2'}),
        ]

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': actions,
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [
                {
                    '_id': '1',
                    '_index': 'searchlight',
                    '_op_type': 'create',
                    '_source': {'disk_format': 'raw', 'name': 'image-1'},
                    '_type': 'OS::Glance::Image'
                },
                {
                    '_id': '2',
                    '_index': 'searchlight',
                    '_op_type': 'create',
                    '_source': {'disk_format': 'raw', 'name': 'image-2'},
                    '_type': 'OS::Glance::Image'
                },
            ],
            'default_index': None,
            'default_type': None
        }
        self.assertEqual(expected, output)

    def test_create_missing_data(self):
        action = _image_fixture('create', '1')
        action.pop('data')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_create_with_default_index(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'default_index': 'searchlight',
            'actions': [_image_fixture('create', '1', index=None)]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': None,
                '_op_type': 'create',
                '_source': {'disk_format': 'raw', 'name': 'image-1'},
                '_type': 'OS::Glance::Image'
            }],
            'default_index': 'searchlight',
            'default_type': None
        }
        self.assertEqual(expected, output)

    def test_create_with_default_doc_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'default_type': 'OS::Glance::Image',
            'actions': [_image_fixture('create', '1', doc_type=None)]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': 'searchlight',
                '_op_type': 'create',
                '_source': {'disk_format': 'raw', 'name': 'image-1'},
                '_type': None
            }],
            'default_index': None,
            'default_type': 'OS::Glance::Image'
        }
        self.assertEqual(expected, output)

    def test_create_with_default_index_and_doc_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'default_index': 'searchlight',
            'default_type': 'OS::Glance::Image',
            'actions': [_image_fixture('create', '1', index=None,
                                       doc_type=None)]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': None,
                '_op_type': 'create',
                '_source': {'disk_format': 'raw', 'name': 'image-1'},
                '_type': None
            }],
            'default_index': 'searchlight',
            'default_type': 'OS::Glance::Image'
        }
        self.assertEqual(expected, output)

    def test_create_missing_id(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('create')]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': None,
                '_index': 'searchlight',
                '_op_type': 'create',
                '_source': {'disk_format': 'raw', 'name': 'image-1'},
                '_type': 'OS::Glance::Image'
            }],
            'default_index': None,
            'default_type': None,
        }
        self.assertEqual(expected, output)

    def test_create_empty_id(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('create', '')]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '',
                '_index': 'searchlight',
                '_op_type': 'create',
                '_source': {'disk_format': 'raw', 'name': 'image-1'},
                '_type': 'OS::Glance::Image'
            }],
            'default_index': None,
            'default_type': None
        }
        self.assertEqual(expected, output)

    def test_create_invalid_index(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('create', index='invalid')]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_create_invalid_doc_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('create', doc_type='invalid')]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_create_missing_index(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('create', '1', index=None)]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_create_missing_doc_type(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('create', '1', doc_type=None)]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_update_missing_id(self):
        action = _image_fixture('update')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_update_missing_data(self):
        action = _image_fixture('update', '1')
        action.pop('data')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_update_using_data(self):
        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [_image_fixture('update', '1')]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': 'searchlight',
                '_op_type': 'update',
                '_type': 'OS::Glance::Image',
                'doc': {'disk_format': 'raw', 'name': 'image-1'}
            }],
            'default_index': None,
            'default_type': None
        }
        self.assertEqual(expected, output)

    def test_update_using_script(self):
        action = _image_fixture('update', '1', script='<sample script>')
        action.pop('data')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': 'searchlight',
                '_op_type': 'update',
                '_type': 'OS::Glance::Image',
                'params': {},
                'script': '<sample script>'
            }],
            'default_index': None,
            'default_type': None,
        }
        self.assertEqual(expected, output)

    def test_update_using_script_and_data(self):
        action = _image_fixture('update', '1', script='<sample script>')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': 'searchlight',
                '_op_type': 'update',
                '_type': 'OS::Glance::Image',
                'params': {'disk_format': 'raw', 'name': 'image-1'},
                'script': '<sample script>'
            }],
            'default_index': None,
            'default_type': None,
        }
        self.assertEqual(expected, output)

    def test_delete_missing_id(self):
        action = _image_fixture('delete')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        self.assertRaises(webob.exc.HTTPBadRequest, self.deserializer.index,
                          request)

    def test_delete_single(self):
        action = _image_fixture('delete', '1')
        action.pop('data')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action]
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [{
                '_id': '1',
                '_index': 'searchlight',
                '_op_type': 'delete',
                '_source': {},
                '_type': 'OS::Glance::Image'
            }],
            'default_index': None,
            'default_type': None
        }
        self.assertEqual(expected, output)

    def test_delete_multiple(self):
        action_1 = _image_fixture('delete', '1')
        action_1.pop('data')
        action_2 = _image_fixture('delete', '2')
        action_2.pop('data')

        request = unit_test_utils.get_fake_request()
        request.body = six.b(jsonutils.dumps({
            'actions': [action_1, action_2],
        }))

        output = self.deserializer.index(request)
        expected = {
            'actions': [
                {
                    '_id': '1',
                    '_index': 'searchlight',
                    '_op_type': 'delete',
                    '_source': {},
                    '_type': 'OS::Glance::Image'
                },
                {
                    '_id': '2',
                    '_index': 'searchlight',
                    '_op_type': 'delete',
                    '_source': {},
                    '_type': 'OS::Glance::Image'
                },
            ],
            'default_index': None,
            'default_type': None
        }
        self.assertEqual(expected, output)


class TestResponseSerializer(test_utils.BaseTestCase):
    def setUp(self):
        super(TestResponseSerializer, self).setUp()
        self.serializer = search.ResponseSerializer()

    def test_plugins_info(self):
        expected = {
            'plugins': [
                {
                    'OS::Glance::Image': {
                        'index': 'searchlight',
                        'type': 'OS::Glance::Image'
                    }
                },
                {
                    'OS::Glance::Metadef': {
                        'index': 'searchlight',
                        'type': 'OS::Glance::Metadef'
                    }
                }
            ]
        }

        request = webob.Request.blank('/v0.1/search')
        response = webob.Response(request=request)
        result = {
            'plugins': [
                {
                    'OS::Glance::Image': {
                        'index': 'searchlight',
                        'type': 'OS::Glance::Image'
                    }
                },
                {
                    'OS::Glance::Metadef': {
                        'index': 'searchlight',
                        'type': 'OS::Glance::Metadef'
                    }
                }
            ]
        }
        self.serializer.search(response, result)
        actual = jsonutils.loads(response.body)
        self.assertEqual(expected, actual)
        self.assertEqual('application/json', response.content_type)

    def test_search(self):
        expected = [{
            'id': '1',
            'name': 'image-1',
            'disk_format': 'raw',
        }]

        request = webob.Request.blank('/v0.1/search')
        response = webob.Response(request=request)
        result = [{
            'id': '1',
            'name': 'image-1',
            'disk_format': 'raw',
        }]
        self.serializer.search(response, result)
        actual = jsonutils.loads(response.body)
        self.assertEqual(expected, actual)
        self.assertEqual('application/json', response.content_type)

    def test_index(self):
        expected = {
            'success': '1',
            'failed': '0',
            'errors': [],
        }

        request = webob.Request.blank('/v0.1/index')
        response = webob.Response(request=request)
        result = {
            'success': '1',
            'failed': '0',
            'errors': [],
        }
        self.serializer.index(response, result)
        actual = jsonutils.loads(response.body)
        self.assertEqual(expected, actual)
        self.assertEqual('application/json', response.content_type)
