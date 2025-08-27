# Copyright 2021 Eugene Frolov.
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

from restalchemy.dm import filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql.dialect.query_builder import q
from restalchemy.tests import fixtures


class SimpleModel(models.ModelWithUUID):
    __tablename__ = "simple_table"

    field_str = properties.property(types.String())
    field_int = properties.property(types.Integer())
    field_bool = properties.property(types.Boolean())


# NOTE(efrolov): Sort model properties for correct ordering in asserts
SimpleModel.properties.sort_properties()


class MySQLQueryBuilderTestCase(unittest.TestCase):

    def setUp(self):
        super(MySQLQueryBuilderTestCase, self).setUp()
        self.Q = q.Q
        self.flt = filters.AND(
            {"field_bool": filters.EQ(True)},
            {"field_int": filters.EQ(0)},
            {"field_str": filters.EQ("FAKE_STR")},
        )

    def tearDown(self):
        super(MySQLQueryBuilderTestCase, self).tearDown()
        del self.Q

    def test_simple_select(self):
        result = self.Q.select(
            model=SimpleModel,
            session=fixtures.SessionFixture(),
        ).compile()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1`",
            result,
        )

    def test_select_with_1_filter(self):
        query = self.Q.select(
            model=SimpleModel,
            session=fixtures.SessionFixture(),
        ).where({"field_bool": filters.EQ(True)})

        result_expression = query.compile()
        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1` "
            "WHERE"
            " `t1`.`field_bool` = %s",
            result_expression,
        )

    def test_select_with_filters_with_and(self):
        query = self.Q.select(
            model=SimpleModel,
            session=fixtures.SessionFixture(),
        ).where(self.flt)

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1` "
            "WHERE"
            " (`t1`.`field_bool` = %s AND"
            " `t1`.`field_int` = %s AND"
            " `t1`.`field_str` = %s)",
            result_expression,
        )
        self.assertEqual([True, 0, "FAKE_STR"], result_values)

    def test_select_with_filters_with_or(self):
        my_filter = filters.OR(
            filters.AND({"field_int": filters.LT(9)}),
            filters.AND(
                {"field_int": filters.GE(1), "field_str": filters.IsNot(None)}
            ),
        )
        query = self.Q.select(
            model=SimpleModel,
            session=fixtures.SessionFixture(),
        ).where(my_filter)

        result_expression = query.compile()
        self.assertEqual(
            "SELECT `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid` "
            "FROM `simple_table` AS `t1` "
            "WHERE (`t1`.`field_int` < %s"
            " OR (`t1`.`field_int` >= %s AND `t1`.`field_str` IS NOT %s))",
            result_expression,
        )

    def test_select_with_empty_filter(self):
        query = self.Q.select(
            model=SimpleModel,
            session=fixtures.SessionFixture(),
        ).where({})

        result_expression = query.compile()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1`",
            result_expression,
        )

    def test_select_two_where_clause(self):
        second_filter = filters.AND({"field_str": filters.EQ("FAKE_STR_TWO")})
        query = (
            self.Q.select(
                model=SimpleModel,
                session=fixtures.SessionFixture(),
            )
            .where(self.flt)
            .where(second_filter)
        )

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1` "
            "WHERE"
            " ((`t1`.`field_bool` = %s AND"
            " `t1`.`field_int` = %s AND"
            " `t1`.`field_str` = %s) AND"
            " `t1`.`field_str` = %s)",
            result_expression,
        )
        self.assertEqual([True, 0, "FAKE_STR", "FAKE_STR_TWO"], result_values)

    def test_select_with_filters_and_limit(self):
        query = (
            self.Q.select(
                model=SimpleModel,
                session=fixtures.SessionFixture(),
            )
            .where(self.flt)
            .limit(2)
        )

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1` "
            "WHERE"
            " (`t1`.`field_bool` = %s AND"
            " `t1`.`field_int` = %s AND"
            " `t1`.`field_str` = %s) "
            "LIMIT 2",
            result_expression,
        )
        self.assertEqual([True, 0, "FAKE_STR"], result_values)

    def test_select_lock_with_filters(self):
        query = (
            self.Q.select(
                model=SimpleModel,
                session=fixtures.SessionFixture(),
            )
            .where(self.flt)
            .for_()
        )

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1` "
            "WHERE"
            " (`t1`.`field_bool` = %s AND"
            " `t1`.`field_int` = %s AND"
            " `t1`.`field_str` = %s) "
            "FOR UPDATE",
            result_expression,
        )
        self.assertEqual([True, 0, "FAKE_STR"], result_values)

    def test_select_lock_with_filters_and_limit(self):
        query = (
            self.Q.select(
                model=SimpleModel,
                session=fixtures.SessionFixture(),
            )
            .where(self.flt)
            .for_()
            .limit(2)
        )

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1` "
            "WHERE"
            " (`t1`.`field_bool` = %s AND"
            " `t1`.`field_int` = %s AND"
            " `t1`.`field_str` = %s) "
            "LIMIT 2 "
            "FOR UPDATE",
            result_expression,
        )
        self.assertEqual([True, 0, "FAKE_STR"], result_values)

    def test_select_order_by_with_filters(self):
        query = (
            self.Q.select(
                model=SimpleModel,
                session=fixtures.SessionFixture(),
            )
            .where(self.flt)
            .order_by("field_str")
        )
        query = query.order_by("field_int", "DESC")

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1` "
            "WHERE"
            " (`t1`.`field_bool` = %s AND"
            " `t1`.`field_int` = %s AND"
            " `t1`.`field_str` = %s) "
            "ORDER BY"
            " `t1`.`field_str` ASC,"
            " `t1`.`field_int` DESC",
            result_expression,
        )
        self.assertEqual([True, 0, "FAKE_STR"], result_values)


class MySQLResultParserTestCase(unittest.TestCase):

    def test_simple_model_result_parser(self):
        row_from_db = {
            "t1_field_bool": "FakeBool",
            "t1_field_int": "FakeInt",
            "t1_field_str": "FakeStr",
            "t1_uuid": "FakeUUID",
        }
        select_clause = q.Q.select(
            SimpleModel,
            session=fixtures.SessionFixture(),
        )

        result = select_clause.parse_row(row_from_db)

        self.assertEqual(
            {
                "field_bool": "FakeBool",
                "field_int": "FakeInt",
                "field_str": "FakeStr",
                "uuid": "FakeUUID",
            },
            result,
        )
