# Copyright 2021 Eugene Frolov <eugene@frolov.net.ru>
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

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.tests.functional import base


class FakeModel(models.Model):

    mutable_dict = properties.property(
        types.Dict(), required=True, mutable=True
    )
    mutable_list = properties.property(
        types.List(), default=list, mutable=True
    )


class DirtyPropertiesTestCase(base.BaseFunctionalTestCase):

    def test_dirty_for_mutable_property_append_values(self):
        target = FakeModel(mutable_dict={"test": "test"})

        target.mutable_dict["xxx"] = "yyyy"

        self.assertTrue(target.is_dirty())

    def test_dirty_for_mutable_property_append_deep_values(self):
        target = FakeModel(mutable_dict={"test": {}})

        target.mutable_dict["test"]["xxx"] = "yyyy"

        self.assertTrue(target.is_dirty())

    def test_dirty_for_mutable_property_change_values(self):
        target = FakeModel(mutable_dict={"test": "test"})

        target.mutable_dict["test"] = "yyyy"

        self.assertTrue(target.is_dirty())

    def test_dirty_for_mutable_property_append_to_default(self):
        target = FakeModel(mutable_dict={})

        target.mutable_list.append("test")

        self.assertTrue(target.is_dirty())
