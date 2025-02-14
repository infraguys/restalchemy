# Copyright 2020 Dima Burmistrov
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

from restalchemy.dm import filters
from restalchemy.tests.unit import base


class FilterEqualityTestCase(base.BaseTestCase):

    def test_filters_equal(self):
        f1 = filters.EQ(4)
        f2 = filters.EQ(4)

        self.assertEqual(f1, f2)

    def test_filters_str_repr(self):
        random_uuid = uuid.uuid4()
        f = filters.EQ(random_uuid)
        self.assertEqual(str(f), str(random_uuid))

    def test_filters_not_equal_type(self):
        f1 = filters.GT(4)
        f2 = filters.EQ(4)

        self.assertNotEqual(f1, f2)

    def test_filters_not_equal_value(self):
        f1 = filters.GT(4)
        f2 = filters.GT(-80)

        self.assertNotEqual(f1, f2)

    def test_expr_filters_equal(self):
        f1 = filters.AND([filters.EQ(4), filters.NE(10)])
        f2 = filters.AND([filters.EQ(4), filters.NE(10)])

        self.assertEqual(f1, f2)

    def test_expr_filters_not_equal_type(self):
        f1 = filters.AND([filters.EQ(4), filters.NE(10)])
        f2 = filters.AND([filters.GT(4), filters.NE(10)])

        self.assertNotEqual(f1, f2)

    def test_expr_filters_not_equal_value(self):
        f1 = filters.AND([filters.EQ(2), filters.NE(10)])
        f2 = filters.AND([filters.EQ(4), filters.NE(10)])

        self.assertNotEqual(f1, f2)
