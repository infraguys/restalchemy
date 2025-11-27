# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

import uuid

import mock

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.common import contexts
from restalchemy.storage import exceptions
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import utils
from restalchemy.tests.functional import base
from restalchemy.tests.functional import consts
from restalchemy.tests import fixtures


FAKE_STR1 = "Fake1"
FAKE_STR2 = "Fake2"
FAKE_INT1 = 1
FAKE_INT2 = 2
FAKE_URI1 = "/fake/00000000-0000-0000-0000-700000000001"
FAKE_URI2 = "/fake/00000000-0000-0000-0000-700000000002"
FAKE_MAC1 = "00:01:02:03:04:05"
FAKE_MAC2 = "10:11:12:13:14:15"
FAKE_TABLE_NAME1 = "Fake-table-name1"
FAKE_TABLE_NAME2 = "Fake-table-name2"
FAKE_UUID1 = uuid.UUID("00000000-0000-0000-0000-700000000003")
FAKE_UUID2 = uuid.UUID("00000000-0000-0000-0000-700000000004")
FAKE_UUID1_STR = str(FAKE_UUID1)
FAKE_UUID2_STR = str(FAKE_UUID2)

URL_TO_DB = "mysql://fake:fake@127.0.0.1/test"


class FakeParentModel(models.ModelWithUUID, orm.SQLStorableMixin):

    __tablename__ = FAKE_TABLE_NAME2


class FakeModel(models.ModelWithUUID, orm.SQLStorableMixin):

    __tablename__ = FAKE_TABLE_NAME1

    test_str_field1 = properties.property(types.String(), default=FAKE_STR1)
    test_str_field2 = properties.property(types.String(), default=FAKE_STR2)

    test_int_field1 = properties.property(types.Integer(), default=FAKE_INT1)
    test_int_field2 = properties.property(types.Integer(), default=FAKE_INT2)

    test_uri_field1 = properties.property(types.Uri(), default=FAKE_URI1)
    test_uri_field2 = properties.property(types.Uri(), default=FAKE_URI2)

    test_mac_field1 = properties.property(types.Mac(), default=FAKE_MAC1)
    test_mac_field2 = properties.property(types.Mac(), default=FAKE_MAC2)

    test_parent_relationship = relationships.relationship(FakeParentModel)


class FakeModelWithValidate(FakeModel):

    def validate(self):
        if self.test_str_field1 == self.test_str_field2:
            raise ValueError


ROW = {
    "test_str_field1": FAKE_STR1,
    "test_str_field2": FAKE_STR2,
    "test_int_field1": FAKE_INT1,
    "test_int_field2": FAKE_INT2,
    "test_uri_field1": FAKE_URI1,
    "test_uri_field2": FAKE_URI2,
    "test_mac_field1": FAKE_MAC1,
    "test_mac_field2": FAKE_MAC2,
    "uuid": FAKE_UUID1_STR,
    "test_parent_relationship": FAKE_UUID2_STR,
}


COLUMNS_NAME = sorted(ROW.keys())
VALUES = tuple()
for key in sorted(ROW.keys()):
    VALUES += (ROW[key],)


def escape(list_of_fields):
    return ["`%s`" % field for field in list_of_fields]


class InsertCaseTestCase(base.BaseFunctionalTestCase):

    @mock.patch("mysql.connector.pooling.MySQLConnectionPool")
    def setUp(self, mysql_pool_mock):
        super(InsertCaseTestCase, self).setUp()

        # configure engine factory
        engines.engine_factory.configure_factory(db_url=URL_TO_DB)
        self.parent_model = FakeParentModel(uuid=FAKE_UUID2)
        self.target_model = FakeModel(
            uuid=FAKE_UUID1, test_parent_relationship=self.parent_model
        )

    def tearDown(self):
        super(InsertCaseTestCase, self).tearDown()

        del self.target_model
        # Note(efrolov): Must be deleted otherwise we will start collect
        #                connections and get an error "too many connections"
        #                from MySQL
        engines.engine_factory.destroy_engine()

    @mock.patch(
        "restalchemy.storage.sql.sessions.MySQLSession",
        return_value=fixtures.SessionFixture(),
    )
    def test_insert_new_model_session_is_none(self, session_mock):

        self.target_model.insert()

        session_mock().execute.assert_called_once_with(
            "INSERT INTO `%s` (%s) VALUES (%s)"
            % (
                FAKE_TABLE_NAME1,
                ", ".join(escape(COLUMNS_NAME)),
                ", ".join(["%s"] * len(VALUES)),
            ),
            VALUES,
        )
        self.assertTrue(session_mock().commit.called)
        self.assertFalse(session_mock().rollback.called)
        self.assertTrue(session_mock().close.called)

    @mock.patch(
        "restalchemy.storage.sql.sessions.MySQLSession",
        return_value=fixtures.SessionFixture(),
    )
    def test_insert_new_model_session_is_none_and_db_error(self, session_mock):

        class CustomException(Exception):
            pass

        session_mock().execute.side_effect = CustomException

        self.assertRaises(
            exceptions.UnknownStorageException, self.target_model.insert
        )

        self.assertFalse(session_mock().commit.called)
        self.assertTrue(session_mock().rollback.called)
        self.assertTrue(session_mock().close.called)

    def test_insert_new_model_with_session(self):
        session_mock = fixtures.SessionFixture()

        self.target_model.insert(session=session_mock)

        session_mock.execute.assert_called_once_with(
            "INSERT INTO `%s` (%s) VALUES (%s)"
            % (
                FAKE_TABLE_NAME1,
                ", ".join(escape(COLUMNS_NAME)),
                ", ".join(["%s"] * len(VALUES)),
            ),
            VALUES,
        )
        self.assertFalse(session_mock.commit.called)
        self.assertFalse(session_mock.rollback.called)
        self.assertFalse(session_mock.close.called)

    def test_insert_new_model_with_session_and_db_error(self):

        session_mock = fixtures.SessionFixture()

        class CustomException(Exception):
            pass

        session_mock.execute.side_effect = CustomException

        self.assertRaises(
            exceptions.UnknownStorageException,
            self.target_model.insert,
            session=session_mock,
        )

        self.assertFalse(session_mock.commit.called)
        self.assertFalse(session_mock.rollback.called)
        self.assertFalse(session_mock.close.called)

    def test_validate(self):
        with self.assertRaises(ValueError):
            FakeModelWithValidate(
                uuid=FAKE_UUID1,
                test_parent_relationship=self.parent_model,
                test_str_field1=FAKE_STR1,
                test_str_field2=FAKE_STR1,
            )


class FakeUpdateModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "test_update"

    field1 = properties.property(types.String(), required=True)
    field2 = properties.property(types.String(), required=True)


class UpdateTestCase(base.BaseFunctionalTestCase):

    def setUp(self):
        super(UpdateTestCase, self).setUp()

        engines.engine_factory.configure_factory(consts.DATABASE_URI)
        engine = engines.engine_factory.get_engine()
        self.engine = engine
        with engine.session_manager() as session:
            session.execute(
                """
                CREATE TABLE IF NOT EXISTS test_update (
                    uuid CHAR(36) PRIMARY KEY,
                    field1 VARCHAR(255) NOT NULL,
                    field2 VARCHAR(255) NOT NULL
                )
            """
            )

    def tearDown(self):
        super(UpdateTestCase, self).tearDown()

        with self.engine.session_manager() as session:
            session.execute("DROP TABLE IF EXISTS test_update;", None)
            # Note(efrolov): Must be deleted otherwise we will start collect
            #                connections and get an error "too many connections"
            #                from MySQL
        engines.engine_factory.destroy_engine()

    def test_update_not_changed_model(self):
        test_model = FakeUpdateModel(field1=FAKE_STR1, field2=FAKE_STR2)
        test_model.save()

        self.assertIsNone(test_model.update())

    def test_force_update_not_changed_model(self):
        test_model = FakeUpdateModel(field1=FAKE_STR1, field2=FAKE_STR2)
        test_model.save()

        self.assertIsNone(test_model.update(force=True))

    def test_validate(self):
        model = FakeModelWithValidate(
            uuid=FAKE_UUID1,
            test_parent_relationship=FakeParentModel(uuid=FAKE_UUID2),
        )
        model.test_str_field2 = FAKE_STR1
        with self.assertRaises(exceptions.UnknownStorageException):
            model.update()


class SavepointModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "savepoint_table"

    field1 = properties.property(types.String(), required=True)
    field2 = properties.property(types.String(), required=True)


class SavepointTestCase(base.BaseFunctionalTestCase):

    def setUp(self):
        super().setUp()

        engines.engine_factory.configure_factory(consts.DATABASE_URI)
        engine = engines.engine_factory.get_engine()
        self.engine = engine
        with engine.session_manager() as session:
            session.execute(
                """
                CREATE TABLE IF NOT EXISTS savepoint_table (
                    uuid CHAR(36) PRIMARY KEY,
                    field1 VARCHAR(255) NOT NULL,
                    field2 VARCHAR(255) NOT NULL
                )
            """
            )

    def tearDown(self):
        super().tearDown()

        with self.engine.session_manager() as session:
            session.execute("DROP TABLE IF EXISTS savepoint_table;", None)
        engines.engine_factory.destroy_engine()

    def test_savepoint_success_result(self):
        with contexts.Context().session_manager():
            test_model = SavepointModel(field1=FAKE_STR1, field2=FAKE_STR2)

            with utils.savepoint():
                test_model.save()

            self.assertEqual(test_model.field1, FAKE_STR1)
            self.assertEqual(test_model.field2, FAKE_STR2)

    def test_savepoint_rollback_result(self):
        with contexts.Context().session_manager():
            test_model = SavepointModel(field1=FAKE_STR1, field2="")
            test_model.save()

            self.assertEqual(test_model.field1, FAKE_STR1)
            self.assertEqual(test_model.field2, "")

            def save_and_raise():
                test_model.field2 = FAKE_STR2
                test_model.save()
                raise ValueError("Error")

            with self.assertRaises(ValueError):
                with utils.savepoint():
                    save_and_raise()

        with contexts.Context().session_manager():
            objects = SavepointModel.objects.get_all()

            self.assertEqual(len(objects), 1)
            self.assertEqual(objects[0].field1, FAKE_STR1)
            self.assertEqual(objects[0].field2, "")

    def test_savepoint_can_continue(self):
        with contexts.Context().session_manager():
            test_model = SavepointModel(field1=FAKE_STR1, field2="")
            test_model.save()

            self.assertEqual(test_model.field1, FAKE_STR1)
            self.assertEqual(test_model.field2, "")

            def save_and_raise():
                test_model.field2 = FAKE_STR2
                test_model.save()
                raise ValueError("Error")

            with self.assertRaises(ValueError):
                with utils.savepoint():
                    save_and_raise()

            test_model.field2 = "foo-value"
            test_model.save()

        with contexts.Context().session_manager():
            objects = SavepointModel.objects.get_all()

            self.assertEqual(len(objects), 1)
            self.assertEqual(objects[0].field1, FAKE_STR1)
            self.assertEqual(objects[0].field2, "foo-value")
