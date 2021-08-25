# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql.dialect import mysql
from restalchemy.storage.sql import tables
from restalchemy.tests.unit import base


class BaseModel(models.ModelWithUUID):
    __tablename__ = 'FAKE_TABLE'

    field_int = properties.property(types.Integer())
    field_str = properties.property(types.String())
    field_bool = properties.property(types.Boolean())


FAKE_TABLE = tables.SQLTable(engine=None,
                             table_name=BaseModel.__tablename__,
                             model=BaseModel)


FAKE_VALUES = [True, 111, "field2", "uuid"]
FAKE_PK_VALUES = ["uuid"]


class MySQLInsertTestCase(base.BaseTestCase):

    def setUp(self):
        self.target = mysql.MySQLInsert(FAKE_TABLE, FAKE_VALUES)

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "INSERT INTO `FAKE_TABLE` (`field_bool`, `field_int`, "
            "`field_str`, `uuid`) VALUES (%s, %s, %s, %s)")


class MySQLUpdateTestCase(base.BaseTestCase):

    def setUp(self):
        TABLE = FAKE_TABLE
        self.target = mysql.MySQLUpdate(TABLE, FAKE_PK_VALUES,
                                        FAKE_VALUES)

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "UPDATE `FAKE_TABLE` SET `field_bool` = %s, `field_int` = %s, "
            "`field_str` = %s WHERE `uuid` = %s")


class MySQLDeleteTestCase(base.BaseTestCase):

    def setUp(self):
        TABLE = FAKE_TABLE

        self.target = mysql.MySQLDelete(TABLE, FAKE_PK_VALUES)

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "DELETE FROM `FAKE_TABLE` WHERE `uuid` = %s")


class MySQLSelectTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FAKE_TABLE

    def test_statement_OR(self):
        ord_filter = collections.OrderedDict()
        for k, v in sorted(zip(self._TABLE.get_column_names(), FAKE_VALUES)):
            ord_filter[k] = dm_filters.EQ(v)
        FAKE_EQ_VALUES = dm_filters.OR(ord_filter)
        target = mysql.MySQLSelect(self._TABLE, FAKE_EQ_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` = %s OR "
            "`field_int` = %s OR `field_str` = %s OR `uuid` = %s)",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_recursive_OR(self):
        FAKE_EQ_VALUES = dm_filters.OR(
            dm_filters.AND(
                {'field_bool': dm_filters.EQ(True)},
                {'field_int': dm_filters.EQ(111)},
            ),
            dm_filters.AND(
                {'field_str': dm_filters.EQ('field2')},
                {'uuid': dm_filters.EQ('uuid')},
            ),
        )
        target = mysql.MySQLSelect(self._TABLE, FAKE_EQ_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE ((`field_bool` = %s AND "
            "`field_int` = %s) OR (`field_str` = %s AND `uuid` = %s))",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_EQ(self):
        FAKE_EQ_VALUES = dm_filters.AND(*[
            {k: dm_filters.EQ(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_EQ_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` = %s AND "
            "`field_int` = %s AND `field_str` = %s AND `uuid` = %s)",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_NE(self):
        FAKE_NE_VALUES = dm_filters.AND(*[
            {k: dm_filters.NE(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_NE_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <> %s AND "
            "`field_int` <> %s AND `field_str` <> %s AND `uuid` <> %s)",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_GT(self):
        FAKE_GT_VALUES = dm_filters.AND(*[
            {k: dm_filters.GT(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_GT_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` > %s AND "
            "`field_int` > %s AND `field_str` > %s AND `uuid` > %s)",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_GE(self):
        FAKE_GE_VALUES = dm_filters.AND(*[
            {k: dm_filters.GE(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_GE_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` >= %s AND "
            "`field_int` >= %s AND `field_str` >= %s AND `uuid` >= %s)",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_LT(self):
        FAKE_LT_VALUES = dm_filters.AND(*[
            {k: dm_filters.LT(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_LT_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` < %s AND "
            "`field_int` < %s AND `field_str` < %s AND `uuid` < %s)",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_LE(self):
        FAKE_LE_VALUES = dm_filters.AND(*[
            {k: dm_filters.LE(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_LE_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s)",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_limit_with_where_clause(self):
        FAKE_LE_VALUES = dm_filters.AND(*[
            {k: dm_filters.LE(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_LE_VALUES, limit=2)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s) "
            "LIMIT 2",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_locked_with_where_clause(self):
        FAKE_LE_VALUES = dm_filters.AND(*[
            {k: dm_filters.LE(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_LE_VALUES, locked=True)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s) "
            "FOR UPDATE",
            result
        )
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_order_by_with_where_clause(self):
        orders = collections.OrderedDict()
        orders['field_str'] = ''
        orders['field_bool'] = 'desc'
        FAKE_LE_VALUES = dm_filters.AND(*[
            {k: dm_filters.LE(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_LE_VALUES,
                                   order_by=orders)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE (`field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `uuid` <= %s) "
            "ORDER BY `field_str` ASC, `field_bool` DESC",
            result)
        self.assertEqual(FAKE_VALUES, target.get_values())

    def test_statement_order_by_without_where_clause(self):
        orders = collections.OrderedDict()
        orders['field_str'] = ''
        orders['field_bool'] = 'desc'
        target = mysql.MySQLSelect(self._TABLE, order_by=orders)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` "
            "ORDER BY `field_str` ASC, `field_bool` DESC",
            result)
        self.assertEqual([], target.get_values())

    def test_statement_order_by_false_order(self):
        FAKE_LE_VALUES = dm_filters.AND(*[
            {k: dm_filters.LE(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLSelect(self._TABLE, FAKE_LE_VALUES,
                                   order_by={'field_str': 'FALSE'})
        self.assertRaises(ValueError, target.get_statement)


class MySQLCustomSelectTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FAKE_TABLE

    def test_custom_where_condition(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE, FAKE_WHERE_CONDITION, FAKE_WHERE_VALUES)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s)",
            result)

    def test_custom_where_condition_with_limit(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE, FAKE_WHERE_CONDITION, FAKE_WHERE_VALUES, limit=2)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) LIMIT 2",
            result)

    def test_custom_where_condition_with_locked(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE, FAKE_WHERE_CONDITION, FAKE_WHERE_VALUES, locked=True)

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) FOR UPDATE",
            result)

    def test_custom_where_condition_with_order_by(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE, FAKE_WHERE_CONDITION, FAKE_WHERE_VALUES,
            order_by={'field_str': ''})

        result = target.get_statement()

        self.assertEqual(
            "SELECT `field_bool`, `field_int`, `field_str`, `uuid` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) "
            "ORDER BY `field_str` ASC",
            result)


class MySQLCountTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FAKE_TABLE

    def test_statement(self):
        target = mysql.MySQLCount(self._TABLE)

        self.assertEqual(
            target.get_statement(),
            "SELECT COUNT(*) as COUNT FROM `FAKE_TABLE`")

    def test_statement_where(self):
        FAKE_EQ_VALUES = dm_filters.AND(*[
            {k: dm_filters.EQ(v)} for k, v in sorted(zip(
                self._TABLE.get_column_names(), FAKE_VALUES))])
        target = mysql.MySQLCount(self._TABLE, FAKE_EQ_VALUES)

        self.assertEqual(
            ("SELECT COUNT(*) as COUNT FROM `FAKE_TABLE` "
             "WHERE (`field_bool` = %s "
             "AND `field_int` = %s AND `field_str` = %s AND `uuid` = %s)"),
            target.get_statement())
