# Copyright 2020 Eugene Frolov
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
from restalchemy.dm import relationships
from restalchemy.tests.unit import base


class MyModel(models.Model):
    pass


class RelationshipTestCase(base.BaseTestCase):

    def test_init_incorrect_value(self):
        with self.assertRaises(TypeError):
            relationships.Relationship(
                property_type=MyModel, value="IncorrectValue"
            )

    def test_init_with_correct_value(self):
        self.assertIsInstance(
            relationships.Relationship(property_type=MyModel, value=MyModel()),
            relationships.Relationship,
        )
