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

from restalchemy.storage.sql.dialect import mysql
from restalchemy.storage.sql import filters
from restalchemy.tests.unit import base
from restalchemy.tests.unit.storage.sql import common


class FakeTable(object):

    name = 'FAKE_TABLE'

    def get_column_names(self, with_pk=True, do_sort=True):
        if with_pk:
            return ["pk", "field_int", "field_str", "field_bool"]
        return ["field_int", "field_str", "field_bool"]

    def get_escaped_column_names(self, with_pk=True, do_sort=True):
        if with_pk:
            return ["`pk`", "`field_int`", "`field_str`", "`field_bool`"]
        return ["`field_int`", "`field_str`", "`field_bool`"]

    def get_pk_names(self, do_sort=True):
        return ["pk"]

    def get_escaped_pk_names(self, do_sort=True):
        return ["`pk`"]


FAKE_VALUES = ["pk", 111, "field2", True]
FAKE_PK_VALUES = ["pk"]


class MySQLInsertTestCase(base.BaseTestCase):

    def setUp(self):
        self.target = mysql.MySQLInsert(FakeTable(), FAKE_VALUES)

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "INSERT INTO `FAKE_TABLE` (`pk`, `field_int`, `field_str`, "
            "`field_bool`) VALUES (%s, %s, %s, %s)")


class MySQLUpdateTestCase(base.BaseTestCase):

    def setUp(self):
        TABLE = FakeTable()
        self.target = mysql.MySQLUpdate(TABLE, FAKE_PK_VALUES,
                                        FAKE_VALUES)

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "UPDATE `FAKE_TABLE` SET `field_int` = %s, `field_str` = %s, "
            "`field_bool` = %s WHERE `pk` = %s")


class MySQLDeleteTestCase(base.BaseTestCase):

    def setUp(self):
        TABLE = FakeTable()

        self.target = mysql.MySQLDelete(TABLE, FAKE_PK_VALUES)

    def test_statement(self):
        self.assertEqual(
            self.target.get_statement(),
            "DELETE FROM `FAKE_TABLE` WHERE `pk` = %s")


class MySQLSelectTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FakeTable()

    def test_statement_EQ(self):
        FAKE_EQ_VALUES = [
            filters.EQ(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_EQ_VALUES)))

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` = %s AND "
            "`field_int` = %s AND `field_str` = %s AND `pk` = %s")

    def test_statement_NE(self):
        FAKE_NE_VALUES = [
            filters.NE(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_NE_VALUES)))

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` <> %s AND "
            "`field_int` <> %s AND `field_str` <> %s AND `pk` <> %s")

    def test_statement_GT(self):
        FAKE_GT_VALUES = [
            filters.GT(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_GT_VALUES)))

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` > %s AND "
            "`field_int` > %s AND `field_str` > %s AND `pk` > %s")

    def test_statement_GE(self):
        FAKE_GE_VALUES = [
            filters.GE(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_GE_VALUES)))

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` >= %s AND "
            "`field_int` >= %s AND `field_str` >= %s AND `pk` >= %s")

    def test_statement_LT(self):
        FAKE_LT_VALUES = [
            filters.LT(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_LT_VALUES)))

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` < %s AND "
            "`field_int` < %s AND `field_str` < %s AND `pk` < %s")

    def test_statement_LE(self):
        FAKE_LE_VALUES = [
            filters.LE(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_LE_VALUES)))

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `pk` <= %s")

    def test_statement_limit_with_where_clause(self):
        FAKE_LE_VALUES = [
            filters.LE(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_LE_VALUES)), limit=2)

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `pk` <= %s LIMIT 2")

    def test_statement_order_by_with_where_clause(self):
        orders = collections.OrderedDict()
        orders['field_str'] = ''
        orders['field_bool'] = 'desc'
        FAKE_LE_VALUES = [
            filters.LE(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_LE_VALUES)),
            order_by=orders)

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE `field_bool` <= %s AND "
            "`field_int` <= %s AND `field_str` <= %s AND `pk` <= %s "
            "ORDER BY `field_str` ASC, `field_bool` DESC")

    def test_statement_order_by_false_order(self):
        FAKE_LE_VALUES = [
            filters.LE(common.AsIsType(), v) for v in FAKE_VALUES]
        target = mysql.MySQLSelect(self._TABLE, dict(zip(
            self._TABLE.get_column_names(), FAKE_LE_VALUES)),
            order_by={'field_str': 'FALSE'})
        self.assertRaises(ValueError, target.get_statement)


class MySQLCustomSelectTestCase(base.BaseTestCase):

    def setUp(self):
        self._TABLE = FakeTable()

    def test_custom_where_condition(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE, FAKE_WHERE_CONDITION, FAKE_WHERE_VALUES)

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s)")

    def test_custom_where_condition_with_limit(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE, FAKE_WHERE_CONDITION, FAKE_WHERE_VALUES, limit=2)

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) LIMIT 2")

    def test_custom_where_condition_with_order_by(self):
        FAKE_WHERE_CONDITION = "NOT (`field_int` => %s AND `field_str` = %s)"
        FAKE_WHERE_VALUES = [1, "2"]
        target = mysql.MySQLCustomSelect(
            self._TABLE, FAKE_WHERE_CONDITION, FAKE_WHERE_VALUES,
            order_by={'field_str': ''})

        result = target.get_statement()

        self.assertEqual(
            result,
            "SELECT `pk`, `field_int`, `field_str`, `field_bool` "
            "FROM `FAKE_TABLE` WHERE "
            "NOT (`field_int` => %s AND `field_str` = %s) "
            "ORDER BY `field_str` ASC")
