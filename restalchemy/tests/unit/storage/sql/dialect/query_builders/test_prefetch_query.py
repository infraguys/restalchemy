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
import uuid

from parameterized import parameterized

from restalchemy.dm import filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.tests import fixtures
from restalchemy.storage.sql.dialect.query_builder import q
from restalchemy.storage.sql import orm
from restalchemy.tests.utils import make_test_name

FAKE_UUID0 = uuid.UUID("00000000-0000-0000-0000-000000000000")
FAKE_UUID1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
FAKE_UUID2 = uuid.UUID("00000000-0000-0000-0000-000000000002")


class SimpleModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "simple_table"

    field_str = properties.property(types.String(), default="FAKE_STR")
    field_int = properties.property(types.Integer(), default=1)
    field_bool = properties.property(types.Boolean(), default=True)


class ModelWithL1Relationships(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "model_with_l1_relationships"

    ref_l0_1 = relationships.relationship(SimpleModel, prefetch=True)
    ref_l0_2 = relationships.relationship(SimpleModel, prefetch=False)


class ModelWithL2Relationships(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "model_with_l2_relationships"

    ref_l1_1 = relationships.relationship(
        ModelWithL1Relationships, prefetch=True
    )
    ref_l1_2 = relationships.relationship(SimpleModel, prefetch=True)
    ref_l1_3 = relationships.relationship(
        ModelWithL1Relationships, prefetch=False
    )


# NOTE(efrolov): Sort model properties for correct ordering in asserts
for model in [SimpleModel, ModelWithL1Relationships, ModelWithL2Relationships]:
    model.properties.sort_properties()


class MySQLPrefetchQueryBuilderTestCase(unittest.TestCase):

    def setUp(self):
        super(MySQLPrefetchQueryBuilderTestCase, self).setUp()
        self.Q = q.Q
        model1 = SimpleModel(uuid=FAKE_UUID1)
        model2 = SimpleModel(uuid=FAKE_UUID2)
        self.flt = filters.AND(
            {"uuid": filters.EQ(FAKE_UUID0)},
            {"ref_l0_1": filters.LE(model1)},
            {"ref_l0_2": filters.NE(model2)},
        )

    def tearDown(self):
        super(MySQLPrefetchQueryBuilderTestCase, self).tearDown()
        del self.Q

    def test_l1_select(self):
        query = self.Q.select(
            model=ModelWithL1Relationships,
            session=fixtures.SessionFixture(),
        )

        result = query.compile()

        self.assertEqual(
            "SELECT"
            " `t1`.`ref_l0_2` AS `t1_ref_l0_2`,"
            " `t1`.`uuid` AS `t1_uuid`,"
            " `t2`.`field_bool` AS `t2_field_bool`,"
            " `t2`.`field_int` AS `t2_field_int`,"
            " `t2`.`field_str` AS `t2_field_str`,"
            " `t2`.`uuid` AS `t2_uuid`"
            " FROM"
            " `model_with_l1_relationships` AS `t1` "
            "LEFT JOIN"
            " `simple_table` AS `t2` "
            "ON"
            " (`t1`.`ref_l0_1` = `t2`.`uuid`)",
            result,
        )

    def test_l1_select_with_filters(self):
        query = self.Q.select(
            model=ModelWithL1Relationships,
            session=fixtures.SessionFixture(),
        ).where(self.flt)

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`ref_l0_2` AS `t1_ref_l0_2`,"
            " `t1`.`uuid` AS `t1_uuid`,"
            " `t2`.`field_bool` AS `t2_field_bool`,"
            " `t2`.`field_int` AS `t2_field_int`,"
            " `t2`.`field_str` AS `t2_field_str`,"
            " `t2`.`uuid` AS `t2_uuid`"
            " FROM"
            " `model_with_l1_relationships` AS `t1` "
            "LEFT JOIN"
            " `simple_table` AS `t2` "
            "ON"
            " (`t1`.`ref_l0_1` = `t2`.`uuid`) "
            "WHERE"
            " (`t1`.`uuid` = %s AND"
            " `t1`.`ref_l0_1` <= %s AND"
            " `t1`.`ref_l0_2` <> %s)",
            result_expression,
        )
        self.assertEqual(
            [
                "00000000-0000-0000-0000-000000000000",
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ],
            result_values,
        )

    def test_select_with_limit(self):
        query = self.Q.select(
            model=ModelWithL1Relationships,
            session=fixtures.SessionFixture(),
        ).limit(100500)

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`ref_l0_2` AS `t1_ref_l0_2`,"
            " `t1`.`uuid` AS `t1_uuid`,"
            " `t2`.`field_bool` AS `t2_field_bool`,"
            " `t2`.`field_int` AS `t2_field_int`,"
            " `t2`.`field_str` AS `t2_field_str`,"
            " `t2`.`uuid` AS `t2_uuid`"
            " FROM"
            " `model_with_l1_relationships` AS `t1` "
            "LEFT JOIN"
            " `simple_table` AS `t2` "
            "ON"
            " (`t1`.`ref_l0_1` = `t2`.`uuid`) "
            "LIMIT 100500",
            result_expression,
        )
        self.assertEqual([], result_values)

    def test_l1_select_lock_with_filters(self):
        query = (
            self.Q.select(
                model=ModelWithL1Relationships,
                session=fixtures.SessionFixture(),
            )
            .where(self.flt)
            .for_()
        )

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`ref_l0_2` AS `t1_ref_l0_2`,"
            " `t1`.`uuid` AS `t1_uuid`,"
            " `t2`.`field_bool` AS `t2_field_bool`,"
            " `t2`.`field_int` AS `t2_field_int`,"
            " `t2`.`field_str` AS `t2_field_str`,"
            " `t2`.`uuid` AS `t2_uuid`"
            " FROM"
            " `model_with_l1_relationships` AS `t1` "
            "LEFT JOIN"
            " `simple_table` AS `t2` "
            "ON"
            " (`t1`.`ref_l0_1` = `t2`.`uuid`) "
            "WHERE"
            " (`t1`.`uuid` = %s AND"
            " `t1`.`ref_l0_1` <= %s AND"
            " `t1`.`ref_l0_2` <> %s) "
            "FOR UPDATE",
            result_expression,
        )
        self.assertEqual(
            [
                "00000000-0000-0000-0000-000000000000",
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ],
            result_values,
        )

    @parameterized.expand(
        [
            (None, "`t1`.`uuid` ASC"),
            ("ASC", "`t1`.`uuid` ASC"),
            ("DESC", "`t1`.`uuid` DESC"),
            (
                "ASC NULLS FIRST",
                "CASE WHEN `t1`.`uuid` IS NULL THEN 0 ELSE 1 END ASC, "
                "`t1`.`uuid` ASC",
            ),
            (
                "ASC NULLS LAST",
                "CASE WHEN `t1`.`uuid` IS NULL THEN 1 ELSE 0 END ASC, "
                "`t1`.`uuid` ASC",
            ),
            (
                "DESC NULLS FIRST",
                "CASE WHEN `t1`.`uuid` IS NULL THEN 0 ELSE 1 END ASC, "
                "`t1`.`uuid` DESC",
            ),
            (
                "DESC NULLS LAST",
                "CASE WHEN `t1`.`uuid` IS NULL THEN 1 ELSE 0 END ASC, "
                "`t1`.`uuid` DESC",
            ),
        ],
        name_func=make_test_name,
    )
    def test_l1_select_order_by(self, sort_dir, correct_clause):
        query = self.Q.select(
            model=ModelWithL1Relationships,
            session=fixtures.SessionFixture(),
        ).order_by("uuid", sort_dir)

        result_expression = query.compile()
        result_values = query.values()

        self.assertEqual(
            "SELECT"
            " `t1`.`ref_l0_2` AS `t1_ref_l0_2`,"
            " `t1`.`uuid` AS `t1_uuid`,"
            " `t2`.`field_bool` AS `t2_field_bool`,"
            " `t2`.`field_int` AS `t2_field_int`,"
            " `t2`.`field_str` AS `t2_field_str`,"
            " `t2`.`uuid` AS `t2_uuid`"
            " FROM"
            " `model_with_l1_relationships` AS `t1` "
            "LEFT JOIN"
            " `simple_table` AS `t2` "
            "ON"
            " (`t1`.`ref_l0_1` = `t2`.`uuid`) "
            f"ORDER BY {correct_clause}",
            result_expression,
        )
        self.assertEqual([], result_values)

    def test_l2_select(self):
        result = self.Q.select(
            model=ModelWithL2Relationships,
            session=fixtures.SessionFixture(),
        ).compile()

        self.assertEqual(
            "SELECT"
            " `t1`.`ref_l1_3` AS `t1_ref_l1_3`,"
            " `t1`.`uuid` AS `t1_uuid`,"
            " `t2`.`ref_l0_2` AS `t2_ref_l0_2`,"
            " `t2`.`uuid` AS `t2_uuid`,"
            " `t3`.`field_bool` AS `t3_field_bool`,"
            " `t3`.`field_int` AS `t3_field_int`,"
            " `t3`.`field_str` AS `t3_field_str`,"
            " `t3`.`uuid` AS `t3_uuid`,"
            " `t4`.`field_bool` AS `t4_field_bool`,"
            " `t4`.`field_int` AS `t4_field_int`,"
            " `t4`.`field_str` AS `t4_field_str`,"
            " `t4`.`uuid` AS `t4_uuid` "
            "FROM"
            " `model_with_l2_relationships` AS `t1` "
            "LEFT JOIN"
            " `model_with_l1_relationships` AS `t2` "
            "ON"
            " (`t1`.`ref_l1_1` = `t2`.`uuid`) "
            "LEFT JOIN"
            " `simple_table` AS `t3` "
            "ON"
            " (`t2`.`ref_l0_1` = `t3`.`uuid`) "
            "LEFT JOIN"
            " `simple_table` AS `t4` "
            "ON"
            " (`t1`.`ref_l1_2` = `t4`.`uuid`)",
            result,
        )


class MySQLResultParserTestCase(unittest.TestCase):

    def test_l1_prefetch_result_parser(self):
        row_from_db = {
            "t1_ref_l0_2": "FakeRsUUID",
            "t1_uuid": "FakeUUID0",
            "t2_field_bool": "FakeBool",
            "t2_field_int": "FakeInt",
            "t2_field_str": "FakeStr",
            "t2_uuid": "FakeUUID1",
        }
        select_clause = q.Q.select(
            ModelWithL1Relationships,
            fixtures.SessionFixture(),
        )

        result = select_clause.parse_row(row_from_db)

        self.assertEqual(
            {
                "uuid": "FakeUUID0",
                "ref_l0_1": {
                    "field_bool": "FakeBool",
                    "field_int": "FakeInt",
                    "field_str": "FakeStr",
                    "uuid": "FakeUUID1",
                },
                "ref_l0_2": "FakeRsUUID",
            },
            result,
        )
