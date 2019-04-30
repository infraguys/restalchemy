# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import mock

from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.tests.unit import base


class FakeModel(models.ModelWithUUID):
    field1 = properties.property(types.Integer(), required=False)


class BasePackerTestCase(base.BaseTestCase):

    def setUp(self):
        super(BasePackerTestCase, self).setUp()
        self._test_instance = packers.BaseResourcePacker(
            resources.ResourceByRAModel(FakeModel), mock.Mock())

    def test_none_field_value(self):
        TEST_OBJ = {'field1': None}

        result = self._test_instance.unpack(TEST_OBJ)

        self.assertDictEqual(result, TEST_OBJ)

#     def test_prepare_resource_dict_type(self):
#         test_value = {'test': 'test', 'test2': 12345}

#         self.assertDictEqual(self.test_instance.prepare_resource(test_value),
#                              test_value)

#     def test_prepare_resource_list_type(self):
#         test_value = ['test', 'test', 'test2', 12345]

#         self.assertListEqual(self.test_instance.prepare_resource(test_value),
#                              test_value)

#     def assertPrepareResourceEqual(self, value):

#         self.assertEqual(self.test_instance.prepare_resource(value), value)

#     def test_prepare_resource_basestring_type(self):
#         self.assertPrepareResourceEqual("FakeValue")
#         self.assertPrepareResourceEqual(u"FakeValue")

#     def test_prepare_resource_int_type(self):
#         self.assertPrepareResourceEqual(10)

#     def test_prepare_resource_long_type(self):
#         self.assertPrepareResourceEqual(long(11))

#     def test_prepare_resource_bool_type(self):
#         self.assertPrepareResourceEqual(True)
#         self.assertPrepareResourceEqual(False)

#     def test_prepare_resource_float_type(self):
#         self.assertPrepareResourceEqual(0.1123)

#     def test_prepare_resource_none_type(self):
#         self.assertPrepareResourceEqual(None)

#     def test_raise_type_error(self):
#         self.assertRaises(TypeError, self.test_instance.prepare_resource,
#                           object())

#     def test_prepare_resource_model_type(self):
#         test_value = {'foo1': 'bar1', 'foo2': 'bar2'}

#         model = mock.MagicMock(spec=models.Model)
#         model.configure_mock(**{
#             'items.return_value': test_value.items()})

#         self.assertDictEqual(self.test_instance.prepare_resource(model),
#                              test_value)

#     @mock.patch.object(routes.RoutesMap, 'get_resource_location',
#                        return_value='FakeUri')
#     def test_prepare_resource_model_type_relationship(self, uri_mock):
#         test_value = {'foo1': 'bar1',
#                       'foo2': mock.MagicMock(spec=models.Model)}
#         result = test_value.copy()
#         result['foo2'] = 'FakeUri'
#         model = mock.MagicMock(spec=models.Model)
#         model.configure_mock(**{
#             'items.return_value': test_value.items()})

#         self.assertDictEqual(self.test_instance.prepare_resource(model),
#                              result)
