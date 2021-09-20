#    Copyright 2021 Eugene Frolov.
#
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

import unittest

from restalchemy.api import resources
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types


class TestModel(models.ModelWithUUID):
    _private_field = properties.property(types.Integer())
    standard_field1 = properties.property(types.Integer())
    standard_field2 = properties.property(types.Integer())
    standard_field3 = properties.property(types.Integer())
    standard_field4 = properties.property(types.Integer())


# NOTE(efrolov): Interface tests
class ResourceByRAModelHiddenFieldsInterfacesTestCase(unittest.TestCase):

    def tearDown(self):
        super(ResourceByRAModelHiddenFieldsInterfacesTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}

    def test_hide_some_fields(self):
        resource = resources.ResourceByRAModel(
            TestModel,
            hidden_fields=['standard_field1', 'standard_field4'],
        )

        result = [name for name, prop in resource.get_fields()
                  if prop.is_public()]

        self.assertEqual(['standard_field2', 'standard_field3', 'uuid'],
                         sorted(result))

    def test_hide_renamed_fields(self):
        resource = resources.ResourceByRAModel(
            TestModel,
            hidden_fields=['standard_field1', 'standard_field4'],
            name_map={'standard_field1': 'new_standard_field1'},
        )

        result = [name for name, prop in resource.get_fields()
                  if prop.is_public()]

        self.assertEqual(['standard_field2', 'standard_field3', 'uuid'],
                         sorted(result))
