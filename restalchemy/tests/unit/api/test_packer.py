# Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
#
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

# TODO(Eugene Frolov): Rewrite tests
import json

import mock
import webob

from restalchemy.api import controllers
from restalchemy.api import field_permissions
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.common import exceptions
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.tests.unit import base


class FakeModel(models.ModelWithUUID):
    field1 = properties.property(types.Integer(), required=False)
    field2 = properties.property(types.Integer())
    field3 = properties.property(types.Integer())
    field4 = properties.property(types.Integer(), required=True)


class TestData(object):
    uuid = None
    field1 = None
    field2 = 2
    field3 = 3
    field4 = 4


class BasePackerTestCase(base.BaseTestCase):

    def setUp(self):
        super(BasePackerTestCase, self).setUp()
        self._test_instance = packers.BaseResourcePacker(
            resources.ResourceByRAModel(FakeModel), mock.Mock()
        )

    def tearDown(self):
        super(BasePackerTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_instance

    def test_none_field_value(self):
        test_data = {"field1": None}

        result = self._test_instance.unpack(test_data)

        self.assertDictEqual(result, test_data)


class PackerFieldPermissionsHiddenTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super(PackerFieldPermissionsHiddenTestCase, self).setUp()
        self._test_resource_packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions(
                        permission=field_permissions.Permissions.HIDDEN
                    )
                ),
            ),
            req,
        )

    def tearDown(self):
        super(PackerFieldPermissionsHiddenTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {}

        result = self._test_resource_packer.pack(new_data)
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field2": 2}

        with self.assertRaises(exceptions.FieldPermissionError) as context:
            self._test_resource_packer.unpack(new_data)

        self.assertEqual(
            "Permission denied for field field2.", str(context.exception)
        )
        self.assertEqual(context.exception.code, 403)


class PackerFieldPermissionsNonDefaultHiddenTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super().setUp()
        self._test_resource_packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions(
                        permission=field_permissions.Permissions.RW
                    ),
                    owner=field_permissions.UniversalPermissions(
                        permission=field_permissions.Permissions.HIDDEN
                    ),
                ),
            ),
            req,
        )

    def tearDown(self):
        super().tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {}

        result = self._test_resource_packer.pack(new_data)
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field2": 2}

        with self.assertRaises(exceptions.FieldPermissionError) as context:
            self._test_resource_packer.unpack(new_data)

        self.assertEqual(
            "Permission denied for field field2.", str(context.exception)
        )
        self.assertEqual(context.exception.code, 403)


class PackerFieldPermissionsRWTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super(PackerFieldPermissionsRWTestCase, self).setUp()
        self._test_resource_packer = packers.BaseResourcePacker(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions()
                ),
            ),
            req,
        )

    def tearDown(self):
        super(PackerFieldPermissionsRWTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {"field2": 2, "field3": 3, "field4": 4}

        result = self._test_resource_packer.pack(new_data)
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field1": None, "field2": 2}

        result = self._test_resource_packer.unpack(new_data)
        self.assertDictEqual(result, new_data)


class JSONPackerIncludeNullTestCase(base.BaseTestCase):
    def setUp(self):
        req = mock.Mock()
        req.context.roles = ["owner"]

        super(JSONPackerIncludeNullTestCase, self).setUp()
        self._test_resource_packer = packers.JSONPackerIncludeNullFields(
            resources.ResourceByRAModel(
                FakeModel,
                fields_permissions=field_permissions.FieldsPermissionsByRole(
                    default=field_permissions.UniversalPermissions()
                ),
            ),
            req,
        )

    def tearDown(self):
        super(JSONPackerIncludeNullTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_resource_packer

    def test_pack(self):
        new_data = TestData()
        expected_data = {
            "field1": None,
            "field2": 2,
            "field3": 3,
            "field4": 4,
            "uuid": None,
        }

        result = json.loads(self._test_resource_packer.pack(new_data))
        self.assertDictEqual(result, expected_data)

    def test_unpack(self):
        new_data = {"field1": None, "field2": 2}

        result = self._test_resource_packer.unpack(json.dumps(new_data))
        self.assertDictEqual(result, new_data)


class MultipartPackerTestCase(base.BaseTestCase):
    _raw_http_request = (
        "POST /v1/docs/5fc2e03d-8b22-4baf-b16d-772c373b98e1/files/ "
        "HTTP/1.1\r\n"
        "Accept: */*\r\n"
        "Content-Length: 200\r\n"
        "Content-Type: multipart/form-data; "
        "boundary=------------------------hSlQJvPejd4JFNPeCJtXm0\r\n"
        "Host: 127.0.0.1:8080\r\n"
        "User-Agent: curl/8.12.1-DEV\r\n"
        "\r\n"
        "--------------------------hSlQJvPejd4JFNPeCJtXm0\r\n"
        'Content-Disposition: form-data; name="data"; filename="test.md"\r\n'
        "Content-Type: */*\r\n"
        "\r\n"
        "test_body\n"
        "\r\n"
        "--------------------------hSlQJvPejd4JFNPeCJtXm0--\r\n"
    )

    def setUp(self):
        super().setUp()
        self._req = webob.Request.from_text(self._raw_http_request)
        self._packer = packers.MultipartPacker(
            resources.ResourceByRAModel(FakeModel),
            self._req,
        )

    def tearDown(self):
        super().tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._packer

    def test_pack(self):
        new_data = b"test"

        result = self._packer.pack(new_data)
        assert result == new_data

    def test_unpack(self):
        result = self._packer.unpack(None)
        assert packers.MultipartPacker._multipart_key in result
        assert len(result[packers.MultipartPacker._parts_key]) == 1
        assert (
            next(iter(result[packers.MultipartPacker._parts_key]["data"].file))
            == b"test_body\n"
        )
