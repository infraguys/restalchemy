# Copyright 2024 George Melikov
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

import mock

from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.common import exceptions
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.tests.unit import base


class FakeModel(models.ModelWithUUID):
    public = properties.property(types.Integer())
    _hidden = properties.property(types.Integer())


class BasePackerTestCase(base.BaseTestCase):

    def setUp(self):
        super(BasePackerTestCase, self).setUp()
        self._test_instance = packers.BaseResourcePacker(
            resources.ResourceByRAModel(
                FakeModel, hidden_fields=["_hidden"], convert_underscore=False
            ),
            mock.Mock(),
        )

    def tearDown(self):
        super(BasePackerTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}
        del self._test_instance

    def test_public_field(self):
        data = {"public": None}

        self._test_instance.unpack(data)

    def test_hidden_field(self):
        data = {"_hidden": None}

        with self.assertRaises(exceptions.ValidationPropertyPrivateError):
            self._test_instance.unpack(data)
