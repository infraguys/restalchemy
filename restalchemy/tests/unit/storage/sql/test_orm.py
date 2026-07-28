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

from unittest import mock

import orjson

from restalchemy.common import exceptions as dm_exceptions
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage import exceptions
from restalchemy.storage.sql import orm
from restalchemy.storage.sql.dialect import exceptions as dialect_exc
from restalchemy.tests.unit import base

FAKE_VALUE_A = "FAKE_A"
FAKE_VALUE_B = "FAKE_B"
FAKE_UUID = "89d423c5-4365-4be2-bde9-2730909a9af8"
#: version 1, where FAKE_UUID is version 4
FAKE_UUID_V1 = "8e1e0c9a-8b3a-11f0-9d3a-0242ac120002"

FAKE_DICT = {"key": "value", "list": [1, 2, 3], "dict": {"a": "A"}}
FAKE_DICT_JSON = orjson.dumps(FAKE_DICT).decode()
FAKE_LIST = [1, "a", None]
FAKE_LIST_JSON = orjson.dumps(FAKE_LIST).decode()


class FakeRestoreModel(models.Model, orm.SQLStorableMixin):
    __tablename__ = "fake_table"

    a = properties.property(types.String())
    b = properties.property(types.String())

    def __init__(self, args, **kwargs):
        super().__init__(*args, **kwargs)
        raise AssertionError("Init method should not be called")


class FakeRestoreModelWithUUID(FakeRestoreModel, models.ModelWithUUID):
    pass


class FakeDirtyRestoreModelWithUUID(FakeRestoreModel, models.ModelWithUUID):
    def is_dirty(self):
        return True


class TestRestoreModelTestCase(base.BaseTestCase):
    def test_init_should_not_be_called(self):
        model = FakeRestoreModel.restore_from_storage(a=FAKE_VALUE_A, b=FAKE_VALUE_B)

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


class FakeRestoreWithJSONModel(models.Model, orm.SQLStorableWithJSONFieldsMixin):
    __tablename__ = "fake_table"
    __jsonfields__ = ["a", "b"]  # noqa: RUF012

    a = properties.property(types.Dict())
    b = properties.property(types.List())


class TestRestoreWithJSONModelTestCase(base.BaseTestCase):
    def test_json_parsed(self):
        model = FakeRestoreWithJSONModel.restore_from_storage(
            a=FAKE_DICT_JSON, b=FAKE_LIST_JSON
        )

        self.assertEqual(model.a, FAKE_DICT)
        self.assertEqual(model.b, FAKE_LIST)

    def test_json_parsed_for_a_page(self):
        rows = [
            {"a": FAKE_DICT_JSON, "b": FAKE_LIST_JSON},
            {"a": FAKE_DICT_JSON, "b": FAKE_LIST_JSON},
        ]

        models_ = FakeRestoreWithJSONModel.restore_many_from_storage(rows)

        self.assertEqual([m.a for m in models_], [FAKE_DICT, FAKE_DICT])
        self.assertEqual([m.b for m in models_], [FAKE_LIST, FAKE_LIST])

    def test_a_page_leaves_natively_decoded_fields_alone(self):
        rows = [{"a": FAKE_DICT, "b": FAKE_LIST}]

        models_ = FakeRestoreWithJSONModel.restore_many_from_storage(rows)

        self.assertEqual(models_[0].a, FAKE_DICT)
        self.assertEqual(models_[0].b, FAKE_LIST)

    def test_a_page_does_not_rewrite_the_rows_it_was_given(self):
        rows = [{"a": FAKE_DICT_JSON, "b": FAKE_LIST_JSON}]

        FakeRestoreWithJSONModel.restore_many_from_storage(rows)

        self.assertEqual(rows, [{"a": FAKE_DICT_JSON, "b": FAKE_LIST_JSON}])

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
            type(model).restore_many_from_storage([{}])
        with self.assertRaises(orm.UndefinedAttribute):
            model._get_prepared_data()


class FakeKeywordRestoreModel(models.Model, orm.SQLStorableMixin):
    """A model that puts its own `restore_from_storage` in the way."""

    __tablename__ = "fake_table"

    a = properties.property(types.String())

    @classmethod
    def restore_from_storage(cls, source=FAKE_VALUE_B, **kwargs):
        obj = super(FakeKeywordRestoreModel, cls).restore_from_storage(**kwargs)
        obj.source = source
        return obj


class FakeRowRestoreModel(models.Model, orm.SQLStorableMixin):
    """A model that settles something on every read, where it is read."""

    __tablename__ = "fake_table"

    a = properties.property(types.String())

    @classmethod
    def restore_row(cls, row, pour=None):
        row = dict(row)
        source = row.pop("source", FAKE_VALUE_B)
        obj = super(FakeRowRestoreModel, cls).restore_row(row, pour)
        obj.source = source
        return obj


class TestWhereEveryReadPassesTestCase(base.BaseTestCase):
    def test_a_page_does_not_go_through_restore_from_storage(self):
        rows = [{"a": FAKE_VALUE_A}, {"a": FAKE_VALUE_A}]

        models_ = FakeKeywordRestoreModel.restore_many_from_storage(rows)

        for model in models_:
            self.assertFalse(hasattr(model, "source"))

    def test_a_single_read_still_goes_through_it(self):
        model = FakeKeywordRestoreModel.restore_from_storage(a=FAKE_VALUE_A)

        self.assertEqual(model.source, FAKE_VALUE_B)

    def test_restore_row_is_where_both_ways_arrive(self):
        page = FakeRowRestoreModel.restore_many_from_storage(
            [{"a": FAKE_VALUE_A}, {"a": FAKE_VALUE_A, "source": "row"}]
        )
        one = FakeRowRestoreModel.restore_from_storage(a=FAKE_VALUE_A)

        self.assertEqual([m.source for m in page], [FAKE_VALUE_B, "row"])
        self.assertEqual(one.source, FAKE_VALUE_B)

    def test_a_page_hands_every_row_the_same_answer(self):
        rows = [{"a": FAKE_VALUE_A} for _ in range(3)]

        with mock.patch.object(
            FakeRowRestoreModel,
            "_get_pour",
            wraps=FakeRowRestoreModel._get_pour,
        ) as get_pour:
            FakeRowRestoreModel.restore_many_from_storage(rows)

        get_pour.assert_called_once_with()


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


class StoragePlanChecksTestCase(base.BaseTestCase):
    """What the plan says is checked, and what it leaves to the type.

    A value the type built itself is of that type; a value the column
    handed back as it was stored is not checked by anybody else.
    """

    class Model(models.ModelWithUUID, orm.SQLStorableMixin):
        __tablename__ = "plan_table"

        name = properties.property(types.String())
        enabled = properties.property(types.Boolean(), default=False)
        stamp = properties.property(types.UTCDateTimeZ(), required=True)

    def _checks(self):
        return {name: check for name, _, check, *_ in self.Model._get_storage_plan()}

    def test_a_value_its_type_built_is_not_checked_again(self):
        checks = self._checks()

        self.assertIsNone(checks["uuid"])
        self.assertIsNone(checks["enabled"])
        self.assertIsNone(checks["stamp"])

    def test_a_value_handed_back_as_stored_is_checked(self):
        checks = self._checks()

        self.assertIsNotNone(checks["name"])

    def test_the_check_that_stays_still_refuses_a_wrong_value(self):
        self.assertRaises(
            dm_exceptions.TypeError,
            self.Model.restore_row,
            {
                "uuid": FAKE_UUID,
                "name": 42,
                "enabled": True,
                "stamp": "2026-08-16 12:00:00.000000",
            },
        )


class VersionOneUUID(types.UUID):
    """A UUID a model will only take one version of.

    It builds its value the way `UUID` does and adds a rule of its own --
    which is the case the plan has to keep checking.
    """

    def validate(self, value):
        return super(VersionOneUUID, self).validate(value) and value.version == 1


class StoragePlanChecksASubclassTestCase(base.BaseTestCase):
    """A type that inherits a conversion may still have its own rule."""

    class Model(models.Model, orm.SQLStorableMixin):
        __tablename__ = "plan_table"

        uuid = properties.property(VersionOneUUID(), id_property=True)

    def test_the_subclass_keeps_its_check(self):
        checks = {name: check for name, _, check, *_ in self.Model._get_storage_plan()}

        self.assertIsNotNone(checks["uuid"])

    def test_the_subclass_check_refuses_what_the_built_in_would_take(self):
        self.assertRaises(
            dm_exceptions.TypeError,
            self.Model.restore_row,
            {"uuid": FAKE_UUID},
        )

    def test_the_subclass_check_takes_what_it_is_meant_to(self):
        model = self.Model.restore_row({"uuid": FAKE_UUID_V1})

        self.assertEqual(str(model.uuid), FAKE_UUID_V1)
