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

import json

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import orm
from restalchemy.tests.unit import base


FAKE_VALUE_A = 'FAKE_A'
FAKE_VALUE_B = 'FAKE_B'

FAKE_DICT = {'key': 'value', 'list': [1, 2, 3], 'dict': {'a': 'A'}}
FAKE_DICT_JSON = json.dumps(FAKE_DICT)
FAKE_LIST = [1, 'a', None]
FAKE_LIST_JSON = json.dumps(FAKE_LIST)


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

    def test_tablename_should_be_defined(self):
        model = type('TestIncompleteRestoreModel',
                     (models.Model, orm.SQLStorableMixin),
                     {})()

        with self.assertRaises(orm.UndefinedAttribute):
            model.get_table()


class TestRestoreWithJSONModel(models.Model,
                               orm.SQLStorableWithJSONFieldsMixin):
    __tablename__ = 'fake_table'
    __jsonfields__ = ['a', 'b']

    a = properties.property(types.Dict())
    b = properties.property(types.List())


class TestRestoreWithJSONModelTestCase(base.BaseTestCase):

    def test_json_parsed(self):
        model = TestRestoreWithJSONModel.restore_from_storage(a=FAKE_DICT_JSON,
                                                              b=FAKE_LIST_JSON)

        self.assertEqual(model.a, FAKE_DICT)
        self.assertEqual(model.b, FAKE_LIST)

    def test_json_dumped(self):
        model = TestRestoreWithJSONModel(a=FAKE_DICT, b=FAKE_LIST)
        prepared_data = model._get_prepared_data()

        self.assertEqual(prepared_data['a'], FAKE_DICT_JSON)
        self.assertEqual(prepared_data['b'], FAKE_LIST_JSON)

    def test_tablename_should_be_defined(self):
        model = type('TestIncompleteRestoreWithJSONModel',
                     (models.Model, orm.SQLStorableWithJSONFieldsMixin),
                     {})()

        with self.assertRaises(orm.UndefinedAttribute):
            model.restore_from_storage()
        with self.assertRaises(orm.UndefinedAttribute):
            model._get_prepared_data()
