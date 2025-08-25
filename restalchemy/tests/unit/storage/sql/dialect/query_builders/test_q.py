# Copyright 2021 George Melikov.
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

from parameterized import parameterized

from restalchemy.storage.sql.dialect.query_builder import common
from restalchemy.storage.sql.dialect.query_builder import q
from restalchemy.tests import fixtures
from restalchemy.tests.utils import make_test_name


class TestOrderByValue(unittest.TestCase):
    def setUp(self):
        self.column = common.Column(
            "1",
            None,
            fixtures.SessionFixture(),
        )

    def test_empty_type(self):
        order = q.OrderByValue(
            self.column,
            fixtures.SessionFixture(),
        )

        self.assertEqual("`1` ASC", order.compile())

    @parameterized.expand(
        [
            ("ASC",),
            ("DESC",),
            ("ASC NULLS FIRST",),
            ("ASC NULLS LAST",),
            ("DESC NULLS FIRST",),
            ("DESC NULLS LAST",),
        ],
        name_func=make_test_name,
    )
    def test_valid_type(self, sort_dir):
        order = q.OrderByValue(
            self.column,
            sort_type=sort_dir,
            session=fixtures.SessionFixture(),
        )
        self.assertTrue(order.compile())

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            q.OrderByValue(
                self.column,
                sort_type="WRONG",
                session=fixtures.SessionFixture(),
            )

    def test_valid_type_lowercase(self):
        order = q.OrderByValue(
            self.column,
            sort_type="desc",
            session=fixtures.SessionFixture(),
        )

        self.assertEqual("`1` DESC", order.compile())
