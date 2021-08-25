# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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
from restalchemy.storage.sql.dialect import query_builders


class SimpleModel(models.ModelWithUUID):
    __tablename__ = 'simple_table'

    field_str = properties.property(types.String())
    field_int = properties.property(types.Integer())
    field_bool = properties.property(types.Boolean())


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.Q = query_builders.Q
        self.flt = filters.AND(
            {'field_bool': filters.EQ(True)},
            {'field_int': filters.EQ(0)},
            {'field_str': filters.EQ('FAKE_STR')},
        )

    def tearDown(self):
        super(BaseTestCase, self).tearDown()
        del self.Q

    def test_simple_select(self):
        result = self.Q.select(SimpleModel).compile()

        self.assertEqual(
            "SELECT"
            " `t1`.`field_bool` AS `t1_field_bool`,"
            " `t1`.`field_int` AS `t1_field_int`,"
            " `t1`.`field_str` AS `t1_field_str`,"
            " `t1`.`uuid` AS `t1_uuid`"
            " FROM"
            " `simple_table` AS `t1`",
            result
        )

    def test_select_with_filters(self):
        query = self.Q.select(SimpleModel).where(self.flt)

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
            result_expression
        )
        self.assertEqual(
            [True, 0, 'FAKE_STR'],
            result_values
        )

    def test_select_with_filters_and_limit(self):
        query = self.Q.select(SimpleModel).where(self.flt).limit(2)

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
            result_expression
        )
        self.assertEqual(
            [True, 0, 'FAKE_STR'],
            result_values
        )

    def test_select_lock_with_filters(self):
        query = self.Q.select(SimpleModel).where(self.flt).for_()

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
            result_expression
        )
        self.assertEqual(
            [True, 0, 'FAKE_STR'],
            result_values
        )

    def test_select_order_by_with_filters(self):
        query = self.Q.select(SimpleModel).where(self.flt).order_by(
            'field_str')
        query = query.order_by('field_int', 'DESC')

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
            " `t1_field_str` ASC,"
            " `t1_field_int` DESC",
            result_expression
        )
        self.assertEqual(
            [True, 0, 'FAKE_STR'],
            result_values
        )
