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

import mock

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.sql.dialect import exceptions as dialect_exc
from restalchemy.storage.sql import orm
from restalchemy.tests.unit import base

FAKE_VALUE_A = "FAKE_A"
FAKE_VALUE_B = "FAKE_B"
FAKE_UUID = "89d423c5-4365-4be2-bde9-2730909a9af8"

FAKE_DICT = {"key": "value", "list": [1, 2, 3], "dict": {"a": "A"}}
FAKE_DICT_JSON = json.dumps(FAKE_DICT, separators=(",", ":"))
FAKE_LIST = [1, "a", None]
FAKE_LIST_JSON = json.dumps(FAKE_LIST, separators=(",", ":"))


class FakeRestoreModel(models.Model, orm.SQLStorableMixin):
    __tablename__ = "fake_table"

    a = properties.property(types.String())
    b = properties.property(types.String())

    def __init__(self, args, **kwargs):
        super(FakeRestoreModel, self).__init__(*args, **kwargs)
        raise AssertionError("Init method should not be called")


class FakeRestoreModelWithUUID(FakeRestoreModel, models.ModelWithUUID):
    pass


class FakeDirtyRestoreModelWithUUID(FakeRestoreModel, models.ModelWithUUID):
    def is_dirty(self):
        return True


class TestRestoreModelTestCase(base.BaseTestCase):

    def test_init_should_not_be_called(self):
        model = FakeRestoreModel.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )

        self.assertEqual(model.a, FAKE_VALUE_A)
        self.assertEqual(model.b, FAKE_VALUE_B)

    def test_tablename_should_be_defined(self):
        model = type(
            "TestIncompleteRestoreModel",
            (models.Model, orm.SQLStorableMixin),
            {},
        )()

        with self.assertRaises(orm.UndefinedAttribute):
            model.get_table()


class FakeRestoreWithJSONModel(
    models.Model, orm.SQLStorableWithJSONFieldsMixin
):
    __tablename__ = "fake_table"
    __jsonfields__ = ["a", "b"]

    a = properties.property(types.Dict())
    b = properties.property(types.List())


class TestRestoreWithJSONModelTestCase(base.BaseTestCase):

    def test_json_parsed(self):
        model = FakeRestoreWithJSONModel.restore_from_storage(
            a=FAKE_DICT_JSON, b=FAKE_LIST_JSON
        )

        self.assertEqual(model.a, FAKE_DICT)
        self.assertEqual(model.b, FAKE_LIST)

    def test_json_dumped(self):
        model = FakeRestoreWithJSONModel(a=FAKE_DICT, b=FAKE_LIST)
        prepared_data = model._get_prepared_data()

        self.assertEqual(prepared_data["a"], FAKE_DICT_JSON)
        self.assertEqual(prepared_data["b"], FAKE_LIST_JSON)

    def test_tablename_should_be_defined(self):
        model = type(
            "TestIncompleteRestoreWithJSONModel",
            (models.Model, orm.SQLStorableWithJSONFieldsMixin),
            {},
        )()

        with self.assertRaises(orm.UndefinedAttribute):
            model.restore_from_storage()
        with self.assertRaises(orm.UndefinedAttribute):
            model._get_prepared_data()


class TestSimplifyModelTestCase(base.BaseTestCase):
    def test_from_model(self):
        model = FakeRestoreModelWithUUID.restore_from_storage(
            a=FAKE_DICT_JSON, b=FAKE_LIST_JSON, uuid=FAKE_UUID
        )

        self.assertEqual(
            FakeRestoreModelWithUUID.to_simple_type(model), str(model.uuid)
        )

    def test_from_id_type(self):
        self.assertEqual(
            FakeRestoreModelWithUUID.to_simple_type(FAKE_UUID), str(FAKE_UUID)
        )


@mock.patch("restalchemy.storage.sql.engines.engine_factory")
class TestModelErrorHandlingCase(base.BaseTestCase):

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.insert")
    def test_insert_model_when_unknown_error_raises(
        self, model_insert_mock, engine_factory_mock
    ):
        model_insert_mock.side_effect = dialect_exc.BaseException(
            code=0, message="Unknown error"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.UnknownStorageException, model.insert)

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update")
    def test_update_model_when_unknown_error_raises(
        self, model_update_mock, engine_factory_mock
    ):
        model_update_mock.side_effect = dialect_exc.BaseException(
            code=0, message="Unknown error"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.UnknownStorageException, model.update)

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.delete")
    def test_delete_model_when_unknown_error_raises(
        self, model_delete_mock, engine_factory_mock
    ):
        model_delete_mock.side_effect = dialect_exc.BaseException(
            code=1213, message="Unknown error"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.UnknownStorageException, model.delete)

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.insert")
    def test_insert_model_when_conflict_error_raises(
        self, model_insert_mock, engine_factory_mock
    ):
        model_insert_mock.side_effect = dialect_exc.Conflict(
            code=1062, message="Conflict is found"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.ConflictRecords, model.insert)

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update")
    def test_update_model_when_conflict_error_raises(
        self, model_update_mock, engine_factory_mock
    ):
        model_update_mock.side_effect = dialect_exc.Conflict(
            code=1062, message="Conflict is found"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.ConflictRecords, model.update)

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.insert")
    def test_insert_model_when_deadlock_error_raises(
        self, model_insert_mock, engine_factory_mock
    ):
        model_insert_mock.side_effect = dialect_exc.DeadLock(
            code=1213, message="Deadlock is found"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.DeadLock, model.insert)

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update")
    def test_update_model_when_deadlock_error_raises(
        self, model_update_mock, engine_factory_mock
    ):
        model_update_mock.side_effect = dialect_exc.DeadLock(
            code=1213, message="Deadlock is found"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.DeadLock, model.update)

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.delete")
    def test_delete_model_when_deadlock_error_raises(
        self, model_delete_mock, engine_factory_mock
    ):
        model_delete_mock.side_effect = dialect_exc.DeadLock(
            code=1213, message="Deadlock is found"
        )
        model = FakeDirtyRestoreModelWithUUID.restore_from_storage(
            a=FAKE_VALUE_A, b=FAKE_VALUE_B
        )
        self.assertRaises(exceptions.DeadLock, model.delete)
