# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2018 Eugene Frolov <eugene@frolov.net.ru>
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

import copy
import unittest

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.memory import engines
from restalchemy.storage.memory import orm


class TestModel1(models.ModelWithUUID, orm.MemoryStorableMixin):

    property1 = properties.property(types.String(), required=True)
    property2 = properties.property(types.Integer(), required=True)


FAKE_STRING1 = 'FakeTest1'
FAKE_STRING2 = 'FakeTest2'
FAKE_STRING3 = 'FakeTest3'
FAKE_INT = 100500


class TestMemoryStorage(unittest.TestCase):

    def setUp(self):
        self.model1 = TestModel1(property1=FAKE_STRING1, property2=FAKE_INT)
        self.model2 = TestModel1(property1=FAKE_STRING2, property2=FAKE_INT)
        self.model3 = TestModel1(property1=FAKE_STRING3, property2=FAKE_INT)

        self.model1.save()
        self.model2.save()
        self.model3.save()

    def tearDown(self):
        engines.engine_factory.get_engine().reset()

    def test_get_one_model(self):
        self.assertEqual(
            self.model1,
            TestModel1.objects.get_one(filters={'uuid': self.model1.uuid}))

    def test_get_one_model_raises_not_found(self):
        self.assertRaises(
            exceptions.RecordNotFound,
            TestModel1.objects.get_one, filters={'property2': FAKE_INT + 1})

    def test_get_one_model_raises_has_many(self):
        self.assertRaises(
            exceptions.HasManyRecords,
            TestModel1.objects.get_one, filters={'property2': FAKE_INT})

    def test_confict(self):
        model4 = copy.copy(self.model1)
        model4._saved = False

        self.assertRaises(exceptions.ConflictRecords, model4.save)

    def test_get_all(self):
        self.assertEqual([self.model1, self.model2, self.model3],
                         TestModel1.objects.get_all())

    def test_get_all_with_limit(self):
        self.assertEqual([self.model1, self.model2],
                         TestModel1.objects.get_all(limit=2))

    def test_get_all_with_filters(self):
        self.assertEqual([self.model1, self.model2, self.model3],
                         TestModel1.objects.get_all(
            filters={'property2': FAKE_INT}))
        self.assertEqual([self.model1], TestModel1.objects.get_all(
            filters={'property1': FAKE_STRING1}))
        self.assertEqual([self.model1], TestModel1.objects.get_all(
            filters={'property1': FAKE_STRING1,
                     'property2': FAKE_INT}))
        self.assertEqual([], TestModel1.objects.get_all(
            filters={'property1': FAKE_STRING1,
                     'property2': FAKE_INT + 1}))

    def test_delete(self):
        self.model2.delete()

        self.assertEqual([self.model1, self.model3],
                         TestModel1.objects.get_all())

    def test_delete_raises_not_found(self):
        self.model2.delete()

        self.assertRaises(exceptions.RecordNotFound,
                          self.model2.delete)

    def test_update(self):
        self.assertIsNone(self.model2.update())

    def test_update_raises_not_found(self):
        model4 = TestModel1(property1=FAKE_STRING1, property2=FAKE_INT)

        self.assertRaises(exceptions.RecordNotFound,
                          model4.update)
