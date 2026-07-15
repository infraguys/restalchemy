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


class ContainsAllFilterTestCase(base.BaseTestCase):
    def test_equal(self):
        self.assertEqual(
            filters.ContainsAll(["a", "b"]), filters.ContainsAll(["a", "b"])
        )

    def test_not_equal_value(self):
        self.assertNotEqual(filters.ContainsAll(["a"]), filters.ContainsAll(["b"]))

    def test_not_equal_type(self):
        self.assertNotEqual(filters.ContainsAll(["a"]), filters.ContainsAny(["a"]))

    def test_repr(self):
        f = filters.ContainsAll(["x"])
        self.assertIn("ContainsAll", repr(f))

    def test_str(self):
        f = filters.ContainsAll(["x", "y"])
        self.assertEqual(str(f), str(["x", "y"]))


class ContainsAnyFilterTestCase(base.BaseTestCase):
    def test_equal(self):
        self.assertEqual(
            filters.ContainsAny(["a", "b"]), filters.ContainsAny(["a", "b"])
        )

    def test_not_equal_value(self):
        self.assertNotEqual(filters.ContainsAny(["a"]), filters.ContainsAny(["b"]))

    def test_not_equal_type(self):
        self.assertNotEqual(filters.ContainsAny(["a"]), filters.ContainsAll(["a"]))

    def test_repr(self):
        f = filters.ContainsAny(["x"])
        self.assertIn("ContainsAny", repr(f))


class JSONFieldsFilterTestCase(base.BaseTestCase):
    def test_plain_scalar_becomes_eq(self):
        f = filters.JSONFields({"kind": "foo"})

        self.assertEqual({"kind": filters.EQ("foo")}, f.value)

    def test_explicit_clause_is_kept_as_is(self):
        f = filters.JSONFields({"value": filters.GT(10)})

        self.assertEqual({"value": filters.GT(10)}, f.value)

    def test_mixed_fields(self):
        f = filters.JSONFields({"kind": "foo", "value": filters.GT(10)})

        self.assertEqual({"kind": filters.EQ("foo"), "value": filters.GT(10)}, f.value)

    def test_equal(self):
        self.assertEqual(
            filters.JSONFields({"kind": "foo"}), filters.JSONFields({"kind": "foo"})
        )

    def test_not_equal_value(self):
        self.assertNotEqual(
            filters.JSONFields({"kind": "foo"}), filters.JSONFields({"kind": "bar"})
        )

    def test_and_expression_value_raises(self):
        self.assertRaises(
            ValueError,
            filters.JSONFields,
            {"kind": filters.AND({"a": filters.EQ(1)})},
        )

    def test_or_expression_value_raises(self):
        self.assertRaises(
            ValueError,
            filters.JSONFields,
            {"kind": filters.OR({"a": filters.EQ(1)})},
        )
