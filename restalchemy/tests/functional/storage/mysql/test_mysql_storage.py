# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import unittest
import uuid

import mock

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import sessions
from restalchemy.tests.functional import consts


FAKE_STR1 = "Fake1"
FAKE_STR2 = "Fake2"
FAKE_INT1 = 1
FAKE_INT2 = 2
FAKE_URI1 = "/fake/00000000-0000-0000-0000-700000000001"
FAKE_URI2 = "/fake/00000000-0000-0000-0000-700000000002"
FAKE_MAC1 = "00:01:02:03:04:05"
FAKE_MAC2 = "10:11:12:13:14:15"
FAKE_TABLE_NAME1 = 'Fake-table-name1'
FAKE_TABLE_NAME2 = 'Fake-table-name2'
FAKE_UUID1 = uuid.UUID("00000000-0000-0000-0000-700000000003")
FAKE_UUID2 = uuid.UUID("00000000-0000-0000-0000-700000000004")
FAKE_UUID1_STR = str(FAKE_UUID1)
FAKE_UUID2_STR = str(FAKE_UUID2)

URL_TO_DB = "mysql://fake:fake@127.0.0.1/test"


class TestParentModel(models.ModelWithUUID, orm.SQLStorableMixin):

    __tablename__ = FAKE_TABLE_NAME2


class TestModel(models.ModelWithUUID, orm.SQLStorableMixin):

    __tablename__ = FAKE_TABLE_NAME1

    test_str_field1 = properties.property(types.String(), default=FAKE_STR1)
    test_str_field2 = properties.property(types.String(), default=FAKE_STR2)

    test_int_field1 = properties.property(types.Integer(), default=FAKE_INT1)
    test_int_field2 = properties.property(types.Integer(), default=FAKE_INT2)

    test_uri_field1 = properties.property(types.Uri(), default=FAKE_URI1)
    test_uri_field2 = properties.property(types.Uri(), default=FAKE_URI2)

    test_mac_field1 = properties.property(types.Mac(), default=FAKE_MAC1)
    test_mac_field2 = properties.property(types.Mac(), default=FAKE_MAC2)

    test_parent_relationship = relationships.relationship(TestParentModel)


ROW = {
    'test_str_field1': FAKE_STR1,
    'test_str_field2': FAKE_STR2,
    'test_int_field1': FAKE_INT1,
    'test_int_field2': FAKE_INT2,
    'test_uri_field1': FAKE_URI1,
    'test_uri_field2': FAKE_URI2,
    'test_mac_field1': FAKE_MAC1,
    'test_mac_field2': FAKE_MAC2,
    'uuid': FAKE_UUID1_STR,
    'test_parent_relationship': FAKE_UUID2_STR}


COLUMNS_NAME = sorted(ROW.keys())
VALUES = tuple()
for key in sorted(ROW.keys()):
    VALUES += (ROW[key],)


def escape(list_of_fields):
    return ["`%s`" % field for field in list_of_fields]


class InsertCase(unittest.TestCase):

    @mock.patch('mysql.connector.pooling.MySQLConnectionPool')
    def setUp(self, mysql_pool_mock):
        # configure engine factory
        engines.engine_factory.configure_factory(
            db_url=URL_TO_DB)
        self.parent_model = TestParentModel(uuid=FAKE_UUID2)
        self.target_model = TestModel(
            uuid=FAKE_UUID1,
            test_parent_relationship=self.parent_model)

    def tearDown(self):
        del self.target_model

    @mock.patch('restalchemy.storage.sql.sessions.MySQLSession')
    def test_insert_new_model_session_is_none(self, session_mock):

        self.target_model.insert()

        session_mock().execute.assert_called_once_with(
            "INSERT INTO `%s` (%s) VALUES (%s)" % (
                FAKE_TABLE_NAME1, ", ".join(escape(COLUMNS_NAME)),
                ", ".join(["%s"] * len(VALUES))),
            VALUES
        )
        self.assertTrue(session_mock().commit.called)
        self.assertFalse(session_mock().rollback.called)
        self.assertTrue(session_mock().close.called)

    @mock.patch('restalchemy.storage.sql.sessions.MySQLSession')
    def test_insert_new_model_session_is_none_and_db_error(
            self, session_mock):

        class CustomException(Exception):
            pass

        session_mock().execute.side_effect = CustomException

        self.assertRaises(CustomException, self.target_model.insert)

        self.assertFalse(session_mock().commit.called)
        self.assertTrue(session_mock().rollback.called)
        self.assertTrue(session_mock().close.called)

    def test_insert_new_model_with_session(self):
        session_mock = mock.MagicMock(spec=sessions.MySQLSession)

        self.target_model.insert(session=session_mock)

        session_mock.execute.assert_called_once_with(
            "INSERT INTO `%s` (%s) VALUES (%s)" % (
                FAKE_TABLE_NAME1, ", ".join(escape(COLUMNS_NAME)),
                ", ".join(["%s"] * len(VALUES))),
            VALUES
        )
        self.assertFalse(session_mock.commit.called)
        self.assertFalse(session_mock.rollback.called)
        self.assertFalse(session_mock.close.called)

    def test_insert_new_model_with_session_and_db_error(self):

        session_mock = mock.MagicMock(spec=sessions.MySQLSession)

        class CustomException(Exception):
            pass

        session_mock.execute.side_effect = CustomException

        self.assertRaises(CustomException, self.target_model.insert,
                          session=session_mock)

        self.assertFalse(session_mock.commit.called)
        self.assertFalse(session_mock.rollback.called)
        self.assertFalse(session_mock.close.called)


class TestUpdateModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "test_update"

    field1 = properties.property(types.String(), required=True)
    field2 = properties.property(types.String(), required=True)


class UpdateTestCase(unittest.TestCase):

    def setUp(self):
        super(UpdateTestCase, self).setUp()
        engines.engine_factory.configure_factory(consts.DATABASE_URI)
        engine = engines.engine_factory.get_engine()
        self.session = engine.get_session()
        self.session.execute("""CREATE TABLE IF NOT EXISTS test_update (
            uuid CHAR(36) NOT NULL,
            field1 VARCHAR(255) NOT NULL,
            field2 VARCHAR(255) NOT NULL,
            PRIMARY KEY (uuid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8;""", None)

    def tearDown(self):
        super(UpdateTestCase, self).tearDown()
        self.session.execute("DROP TABLE IF EXISTS test_update;", None)

    def test_update_not_changed_model(self):
        test_model = TestUpdateModel(field1=FAKE_STR1, field2=FAKE_STR2)
        test_model.save()

        self.assertIsNone(test_model.update())

    def test_force_update_not_changed_model(self):
        test_model = TestUpdateModel(field1=FAKE_STR1, field2=FAKE_STR2)
        test_model.save()

        self.assertIsNone(test_model.update(force=True))
