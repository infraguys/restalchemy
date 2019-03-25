# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2019 Eugene Frolov
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
from restalchemy.storage.sql import orm
from restalchemy.tests.unit import base


FAKE_VALUE_A = 'FAKE_A'
FAKE_VALUE_B = 'FAKE_B'


class TestRestoreModel(models.Model, orm.SQLStorableMixin):
    __tablename__ = 'fake_table'

    a = properties.property(types.String())
    b = properties.property(types.String())

    def __init__(self, args, **kwargs):
        super(TestRestoreModel, self).__init__(*args, **kwargs)
        raise AssertionError("Init method should not be called")


class TestRestoreModelTestCase(base.BaseTestCase):

    def test_init_should_not_be_called(self):

        model = TestRestoreModel.restore_from_storage(a=FAKE_VALUE_A,
                                                      b=FAKE_VALUE_B)

        self.assertEqual(model.a, FAKE_VALUE_A)
        self.assertEqual(model.b, FAKE_VALUE_B)
