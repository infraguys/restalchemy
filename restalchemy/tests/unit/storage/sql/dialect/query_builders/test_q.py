# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

from restalchemy.storage.sql.dialect.query_builder import common
from restalchemy.storage.sql.dialect.query_builder import q


class TestOrderByValue(unittest.TestCase):
    def setUp(self):
        self.column = common.Column('1', None)

    def test_empty_type(self):
        order = q.OrderByValue(self.column)

        self.assertEqual('`1` ASC', order.compile())

    def test_valid_type(self):
        order = q.OrderByValue(self.column, sort_type='DESC')

        self.assertEqual('`1` DESC', order.compile())

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            q.OrderByValue(self.column, sort_type='WRONG')

    def test_valid_type_lowercase(self):
        order = q.OrderByValue(self.column, sort_type='desc')

        self.assertEqual('`1` DESC', order.compile())
