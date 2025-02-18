# Copyright 2017 Eugene Frolov <eugene@frolov.net.ru>
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

import collections
import mock

from mysql.connector import errors
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql.dialect import exceptions as dialect_exc
from restalchemy.storage.sql.dialect import mysql
from restalchemy.storage.sql import tables
from restalchemy.tests.unit import base
from restalchemy.tests import fixtures


class BaseModel(models.ModelWithUUID):
    __tablename__ = "FAKE_TABLE"

    field_int = properties.property(types.Integer())
    field_str = properties.property(types.String())
    field_bool = properties.property(types.Boolean())


class MultipleIdModel(BaseModel):
    tenant_id = properties.property(types.String(), id_property=True)

    @classmethod
    def get_id_property(cls):
        return {"tenant_id": cls.properties["tenant_id"]}


FAKE_TABLE = tables.SQLTable(
    engine=None, table_name=BaseModel.__tablename__, model=BaseModel
)

EXTENDED_FAKE_TABLE = tables.SQLTable(
    engine=None,
    table_name=MultipleIdModel.__tablename__,
    model=MultipleIdModel,
)


FAKE_VALUES = [True, 111, "field2", "uuid"]
FAKE_PK_VALUES = ["uuid"]
EXTENDED_FAKE_VALUES = [True, 111, "field2", "tenant_id", "uuid"]
EXTENDED_FAKE_PK_VALUES = ["uuid", "tenant_id"]


class AbstractDialectCommandTestMixin(object):
    @mock.patch(
        "restalchemy.storage.sql.dialect.base.AbstractDialectCommand.execute",
        side_effect=errors.DatabaseError(
            "deadlock", errno=1213, sqlstate=1213
        ),
    )
    def test_execute_when_errno_1213(self, command_mock):
        with self.assertRaises(dialect_exc.DeadLock) as ctx:
            self.target.execute()
        self.assertEqual(1213, ctx.exception.code)
        self.assertEqual("deadlock", str(ctx.exception))

    @mock.patch(
        "restalchemy.storage.sql.dialect.base.AbstractDialectCommand.execute",
        side_effect=errors.DatabaseError(
            "conflict", errno=1062, sqlstate=1062
        ),
    )
    def test_execute_when_errno_1062(self, command_mock):
        with self.assertRaises(dialect_exc.Conflict) as ctx:
            self.target.execute()
        self.assertEqual(1062, ctx.exception.code)
        self.assertEqual("conflict", str(ctx.exception))

    @mock.patch(
        "restalchemy.storage.sql.dialect.base.AbstractDialectCommand.execute",
        side_effect=errors.DatabaseError("access denied", errno=1045),
    )
    def test_execute_when_errno_1045(self, command_mock):
        with self.assertRaises(errors.DatabaseError) as ctx:
            self.target.execute()
        self.assertEqual(1045, ctx.exception.errno)
        self.assertEqual("access denied", ctx.exception.msg)


class MySQLInsertTestCase(base.BaseTestCase, AbstractDialectCommandTestMixin):

    def setUp(self):
        self.target = mysql.MySQLInsert(
            FAKE_TABLE,
            FAKE_VALUES,
            session=fixtures.SessionFixture(),
        )

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "INSERT INTO `FAKE_TABLE` (`field_bool`, `field_int`, "
            "`field_str`, `uuid`) VALUES (%s, %s, %s, %s)",
        )


class MySQLUpdateTestCase(base.BaseTestCase, AbstractDialectCommandTestMixin):

    def setUp(self):
        TABLE = FAKE_TABLE
        self.target = mysql.MySQLUpdate(
            TABLE,
            FAKE_PK_VALUES,
            FAKE_VALUES,
            session=fixtures.SessionFixture(),
        )

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "UPDATE `FAKE_TABLE` SET `field_bool` = %s, `field_int` = %s, "
            "`field_str` = %s WHERE `uuid` = %s",
        )


class MySQLUpdateMultipleIdTestCase(
    base.BaseTestCase, AbstractDialectCommandTestMixin
):

    def setUp(self):
        TABLE = EXTENDED_FAKE_TABLE
        self.target = mysql.MySQLUpdate(
            TABLE,
            EXTENDED_FAKE_PK_VALUES,
            EXTENDED_FAKE_VALUES,
            session=fixtures.SessionFixture(),
        )

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "UPDATE `FAKE_TABLE` SET `field_bool` = %s, `field_int` = %s, "
            "`field_str` = %s WHERE `tenant_id` = %s AND `uuid` = %s",
        )


class MySQLDeleteTestCase(base.BaseTestCase, AbstractDialectCommandTestMixin):

    def setUp(self):
        TABLE = FAKE_TABLE

        self.target = mysql.MySQLDelete(
            TABLE,
            FAKE_PK_VALUES,
            session=fixtures.SessionFixture(),
        )

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "DELETE FROM `FAKE_TABLE` WHERE `uuid` = %s",
        )


class MySQLDeleteMultipleIdTestCase(
    base.BaseTestCase, AbstractDialectCommandTestMixin
):

    def setUp(self):
        TABLE = EXTENDED_FAKE_TABLE

        self.target = mysql.MySQLDelete(
            TABLE,
            EXTENDED_FAKE_VALUES,
            session=fixtures.SessionFixture(),
        )

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "DELETE FROM `FAKE_TABLE` WHERE `tenant_id` = %s AND `uuid` = %s",
        )


class MySQLSelectTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FAKE_TABLE

    def test_statement_OR(self):
        session = mock.Mock()
        ord_filter = collections.OrderedDict()
        for k, v in sorted(
            zip(self._TABLE.get_column_names(session), FAKE_VALUES)
        ):
            ord_filter[k] = dm_filters.EQ(v)
        FAKE_EQ_VALUES = dm_filters.OR(ord_filter)
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_EQ_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` = %s OR "
            "`field_int` = %s OR `field_str` = %s OR `uuid` = %s)",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_recursive_OR(self):
        FAKE_EQ_VALUES = dm_filters.OR(
            dm_filters.AND(
                {"field_bool": dm_filters.EQ(True)},
                {"field_int": dm_filters.EQ(111)},
            ),
            dm_filters.AND(
                {"field_str": dm_filters.EQ("field2")},
                {"uuid": dm_filters.EQ("uuid")},
            ),
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_EQ_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE ((`field_bool` = %s AND "
            "`field_int` = %s) OR (`field_str` = %s AND `uuid` = %s))",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_EQ(self):
        session = mock.Mock()
        FAKE_EQ_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.EQ(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_EQ_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` = %s AND "
            "`field_int` = %s AND `field_str` = %s AND `uuid` = %s)",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_NE(self):
        session = mock.Mock()
        FAKE_NE_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.NE(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_NE_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <> %s AND "
            "`field_int` <> %s AND `field_str` <> %s AND `uuid` <> %s)",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_GT(self):
        session = mock.Mock()
        FAKE_GT_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.GT(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_GT_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` > %s AND "
            "`field_int` > %s AND `field_str` > %s AND `uuid` > %s)",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_GE(self):
        session = mock.Mock()
        FAKE_GE_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.GE(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_GE_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` >= %s AND "
            "`field_int` >= %s AND `field_str` >= %s AND `uuid` >= %s)",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_LT(self):
        session = mock.Mock()
        FAKE_LT_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.LT(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_LT_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` < %s AND "
            "`field_int` < %s AND `field_str` < %s AND `uuid` < %s)",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_LE(self):
        session = mock.Mock()
        FAKE_LE_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.LE(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_LE_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s)",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_limit_with_where_clause(self):
        session = mock.Mock()
        FAKE_LE_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.LE(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_LE_VALUES,
            limit=2,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s) "
            "LIMIT 2",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_locked_with_where_clause(self):
        session = mock.Mock()
        FAKE_LE_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.LE(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_LE_VALUES,
            locked=True,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s) "
            "FOR UPDATE",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_order_by_with_where_clause(self):
        session = mock.Mock()
        orders = collections.OrderedDict()
        orders["field_str"] = ""
        orders["field_bool"] = "desc"
        FAKE_LE_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.LE(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_LE_VALUES,
            order_by=orders,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s) "
            "ORDER BY `field_str` ASC, `field_bool` DESC",
            result,
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_order_by_without_where_clause(self):
        orders = collections.OrderedDict()
        orders["field_str"] = ""
        orders["field_bool"] = "desc"
        target = mysql.MySQLSelect(
            self._TABLE,
            order_by=orders,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` "
            "ORDER BY `field_str` ASC, `field_bool` DESC",
            result,
        )
        self.assertEqual([], target.get_values())

    def test_statement_order_by_false_order(self):
        session = mock.Mock()
        FAKE_LE_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.LE(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLSelect(
            self._TABLE,
            filters=FAKE_LE_VALUES,
            order_by={"field_str": "FALSE"},
            session=fixtures.SessionFixture(),
        )
        self.assertRaises(ValueError, target.get_statement)


class MySQLCustomSelectTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FAKE_TABLE

    def test_custom_where_condition(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE,
            FAKE_WHERE_CONDITION,
            FAKE_WHERE_VALUES,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s)",
            result,
        )

    def test_custom_where_condition_with_limit(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE,
            FAKE_WHERE_CONDITION,
            FAKE_WHERE_VALUES,
            limit=2,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) LIMIT 2",
            result,
        )

    def test_custom_where_condition_with_locked(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE,
            FAKE_WHERE_CONDITION,
            FAKE_WHERE_VALUES,
            locked=True,
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) FOR UPDATE",
            result,
        )

    def test_custom_where_condition_with_order_by(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE,
            FAKE_WHERE_CONDITION,
            FAKE_WHERE_VALUES,
            order_by={"field_str": ""},
            session=fixtures.SessionFixture(),
        )

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) "
            "ORDER BY `field_str` ASC",
            result,
        )


class MySQLCountTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FAKE_TABLE

    def test_statement(self):
        target = mysql.MySQLCount(
            self._TABLE,
            session=fixtures.SessionFixture(),
        )

        self.assertEqual(
            target.get_statement(),
            "SELECT COUNT(*) as count FROM `FAKE_TABLE`",
        )

    def test_statement_where(self):
        session = mock.Mock()
        FAKE_EQ_VALUES = dm_filters.AND(
            *[
                {k: dm_filters.EQ(v)}
                for k, v in sorted(
                    zip(self._TABLE.get_column_names(session), FAKE_VALUES)
                )
            ]
        )
        target = mysql.MySQLCount(
            self._TABLE,
            filters=FAKE_EQ_VALUES,
            session=fixtures.SessionFixture(),
        )

        self.assertEqual(
            (
                "SELECT COUNT(*) as count FROM `FAKE_TABLE` "
                "WHERE (`field_bool` = %s "
                "AND `field_int` = %s AND `field_str` = %s AND `uuid` = %s)"
            ),
            target.get_statement(),
        )
