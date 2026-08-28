# Copyright 2026 Genesis Corporation
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

from unittest import mock

from restalchemy.api import filter_lang
from restalchemy.common import exceptions as ra_exc
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models as dm_models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.storage.sql import filters as sql_filters
from restalchemy.tests.unit import base


class FilterModel(dm_models.ModelWithUUID, dm_models.ModelWithTags):
    name = properties.property(types.String(), default="")
    size = properties.property(types.Integer(), default=0)
    spec = properties.property(types.Dict(), default=dict)


def _restriction(field, comparator, value, quoted=False):
    return filter_lang.Restriction(
        [filter_lang.Literal(field)],
        comparator,
        filter_lang.Literal(value, quoted),
    )


class ParserTestCase(base.BaseTestCase):
    def test_an_empty_filter_parses_to_nothing(self):
        self.assertIsNone(filter_lang.parse(""))
        self.assertIsNone(filter_lang.parse("   "))

    def test_a_single_restriction(self):
        self.assertEqual(
            _restriction("name", "=", "vm1", quoted=True),
            filter_lang.parse('name = "vm1"'),
        )

    def test_spaces_around_the_comparator_are_optional(self):
        self.assertEqual(filter_lang.parse("size>10"), filter_lang.parse("size > 10"))

    def test_whitespace_between_factors_is_an_implicit_and(self):
        self.assertEqual(
            filter_lang.parse("name = a AND size = 1"),
            filter_lang.parse("name = a size = 1"),
        )

    def test_or_binds_tighter_than_and(self):
        # AIP-160's precedence, which is not the usual one:
        # `a OR b AND c OR d` is `(a OR b) AND (c OR d)`.
        parsed = filter_lang.parse("name = a OR name = b AND size = 1 OR size = 2")

        self.assertEqual(
            filter_lang.Conjunction(
                filter_lang.Disjunction(
                    _restriction("name", "=", "a"),
                    _restriction("name", "=", "b"),
                ),
                filter_lang.Disjunction(
                    _restriction("size", "=", "1"),
                    _restriction("size", "=", "2"),
                ),
            ),
            parsed,
        )

    def test_parentheses_override_the_precedence(self):
        self.assertEqual(
            filter_lang.Disjunction(
                _restriction("name", "=", "a"),
                filter_lang.Conjunction(
                    _restriction("name", "=", "b"),
                    _restriction("size", "=", "1"),
                ),
            ),
            filter_lang.parse("name = a OR (name = b AND size = 1)"),
        )

    def test_not_negates_the_following_simple(self):
        self.assertEqual(
            filter_lang.Negation(_restriction("name", "=", "a")),
            filter_lang.parse("NOT name = a"),
        )

    def test_a_quoted_value_keeps_its_punctuation(self):
        parsed = filter_lang.parse('tags:"env:prod"')

        self.assertEqual(":", parsed.comparator)
        self.assertEqual("env:prod", parsed.value.text)
        self.assertTrue(parsed.value.quoted)

    def test_quoting_is_remembered(self):
        self.assertTrue(filter_lang.parse('name = "null"').value.quoted)
        self.assertFalse(filter_lang.parse("name = null").value.quoted)

    def test_escapes_inside_a_string(self):
        self.assertEqual('a"b', filter_lang.parse('name = "a\\"b"').value.text)

    def test_a_dot_between_digits_stays_in_the_number(self):
        parsed = filter_lang.parse("size = 1.5")

        self.assertEqual(1, len(parsed.path))
        self.assertEqual("1.5", parsed.value.text)

    def test_a_dot_between_names_is_a_traversal(self):
        parsed = filter_lang.parse("spec.kind = totp")

        self.assertEqual(["spec", "kind"], [p.text for p in parsed.path])

    def test_lowercase_and_is_a_value_not_a_keyword(self):
        # The keywords are uppercase, so `and` remains an ordinary word.
        self.assertEqual(
            _restriction("name", "=", "and"), filter_lang.parse("name=and")
        )

    def test_adjacent_factors_need_whitespace(self):
        self.assertRaises(
            ra_exc.ValidationFilterSyntaxError,
            filter_lang.parse,
            "(name = a)(size = 1)",
        )

    def test_an_unterminated_string(self):
        self.assertRaises(
            ra_exc.ValidationFilterSyntaxError, filter_lang.parse, 'name = "vm1'
        )

    def test_an_unclosed_parenthesis(self):
        self.assertRaises(
            ra_exc.ValidationFilterSyntaxError, filter_lang.parse, "(name = a"
        )

    def test_a_lone_bang(self):
        self.assertRaises(
            ra_exc.ValidationFilterSyntaxError, filter_lang.parse, "name ! a"
        )

    def test_a_comma_names_a_function_which_is_unsupported(self):
        self.assertRaises(
            ra_exc.ValidationFilterSyntaxError, filter_lang.parse, "f(a, b)"
        )

    def test_a_missing_value(self):
        self.assertRaises(
            ra_exc.ValidationFilterSyntaxError, filter_lang.parse, "name ="
        )

    def test_too_many_nodes_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterTooComplexError,
            filter_lang.parse,
            " AND ".join(["name = a"] * 40),
        )

    def test_too_deep_a_nesting_is_refused(self):
        depth = filter_lang.MAX_DEPTH + 1

        self.assertRaises(
            ra_exc.ValidationFilterTooComplexError,
            filter_lang.parse,
            "(" * depth + "name = a" + ")" * depth,
        )

    def test_the_caps_are_per_call(self):
        self.assertRaises(
            ra_exc.ValidationFilterTooComplexError,
            filter_lang.parse,
            "name = a AND size = 1",
            2,
        )

    def test_too_long_a_string_is_refused_before_it_is_scanned(self):
        # The node cap cannot do this job: it is counted by the parser,
        # and the parser runs after the whole string has been tokenized.
        long_one = "name = a " * filter_lang.MAX_LENGTH

        with mock.patch.object(
            filter_lang, "tokenize", side_effect=AssertionError("scanned")
        ):
            self.assertRaises(
                ra_exc.ValidationFilterTooComplexError,
                filter_lang.parse,
                long_one,
            )

    def test_the_length_cap_is_per_call(self):
        self.assertRaises(
            ra_exc.ValidationFilterTooComplexError,
            filter_lang.parse,
            "name = a",
            filter_lang.MAX_NODES,
            filter_lang.MAX_DEPTH,
            4,
        )

    def test_a_lowercase_keyword_says_which_one_it_is(self):
        # `and` parses as a field name, and the error it would otherwise
        # get names the wrong problem.
        with self.assertRaises(ra_exc.ValidationFilterSyntaxError) as caught:
            filter_lang.parse("name = a and size = 1")

        self.assertIn("AND", str(caught.exception))

    def test_a_quoted_keyword_is_still_a_value(self):
        self.assertEqual(
            _restriction("name", "=", "and", quoted=True),
            filter_lang.parse('name = "and"'),
        )


class BinderTestCase(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        self._resolver = filter_lang.ModelFieldResolver(
            FilterModel, dialect="postgresql"
        )

    def _build(self, text):
        return filter_lang.compile_filter(text, self._resolver)

    def test_an_empty_filter_binds_to_no_filters(self):
        self.assertEqual({}, self._build(""))

    def test_equality_carries_the_parsed_value(self):
        built = self._build("size = 10")

        self.assertIsInstance(built["size"], dm_filters.EQ)
        # The value went through the field's type, so it is an int.
        self.assertEqual(10, built["size"].value)

    def test_every_comparator_maps_to_its_clause(self):
        for comparator, clause in (
            ("=", dm_filters.EQ),
            ("!=", dm_filters.NE),
            ("<", dm_filters.LT),
            ("<=", dm_filters.LE),
            (">", dm_filters.GT),
            (">=", dm_filters.GE),
        ):
            built = self._build(f"size {comparator} 10")

            self.assertIsInstance(built["size"], clause)

    def test_null_becomes_is_rather_than_equals(self):
        self.assertEqual({"name": dm_filters.Is(None)}, self._build("name = null"))
        self.assertEqual({"name": dm_filters.IsNot(None)}, self._build("name != null"))

    def test_a_quoted_null_is_a_string(self):
        built = self._build('name = "null"')

        self.assertIsInstance(built["name"], dm_filters.EQ)
        self.assertEqual("null", built["name"].value)

    def test_null_does_not_compare_with_an_ordering_operator(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError, self._build, "size > null"
        )

    def test_has_on_an_array_is_containment(self):
        built = self._build('tags:"env:prod"')

        self.assertIsInstance(built["tags"], dm_filters.ContainsAll)
        self.assertEqual(["env:prod"], built["tags"].value)

    def test_has_a_star_asks_whether_the_field_is_set(self):
        self.assertEqual({"name": dm_filters.IsNot(None)}, self._build("name:*"))

    def test_a_quoted_star_is_an_asterisk(self):
        # ...and so needs an array field, like any other element.
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError, self._build, 'name:"*"'
        )

    def test_has_needs_an_array_field(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError, self._build, "name:vm1"
        )

    def test_traversal_becomes_a_json_filter(self):
        built = self._build("spec.kind = totp")

        self.assertIsInstance(built["spec"], dm_filters.JSONFields)
        self.assertEqual({"kind": dm_filters.EQ("totp")}, built["spec"].value)

    def test_a_json_value_keeps_the_type_it_was_written_as(self):
        # PostgreSqlJSONFields picks its SQL cast off the Python type, so
        # `10` and `"10"` are not interchangeable.
        self.assertEqual(
            10, self._build("spec.period = 10")["spec"].value["period"].value
        )
        self.assertEqual(
            "10", self._build('spec.period = "10"')["spec"].value["period"].value
        )

    def test_traversal_needs_a_json_field(self):
        # `("name"->>'x')` on a text column is an undefined operator, and
        # PostgreSQL raising it would be a 500 for a client error.
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError, self._build, 'name."x" = 1'
        )

    def test_traversal_deeper_than_one_key_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError, self._build, "spec.a.b = 1"
        )

    def test_a_json_key_is_held_to_a_bare_name(self):
        # It reaches the SQL as text, not as a parameter; quoting one buys
        # no alphabet. See `sql.filters._JSONFieldClause`.
        for key in (
            r"a\') IS NOT NULL OR 1=1 --",
            "%s",
            "a'b",
            "a b",
            "",
        ):
            with self.subTest(key=key):
                self.assertRaises(
                    ra_exc.ValidationFilterIncompatibleError,
                    self._build,
                    'spec."{}" = 1'.format(key.replace("\\", "\\\\")),
                )

    def test_an_ordinary_json_key_still_binds(self):
        for key in ("kind", "device_id", "a-b", "период"):
            with self.subTest(key=key):
                built = self._build(f'spec."{key}" = 1')

                self.assertEqual([key], list(built["spec"].value))

    def test_an_unknown_field_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError, self._build, "nope = 1"
        )

    def test_a_bare_literal_is_refused(self):
        self.assertRaises(ra_exc.ValidationFilterIncompatibleError, self._build, "prod")

    def test_a_value_the_field_type_rejects_is_refused(self):
        self.assertRaises(
            ra_exc.ValidationFilterSyntaxError, self._build, "size = notanumber"
        )

    def test_and_builds_a_conjunction(self):
        built = self._build("name = a AND size = 1")

        self.assertIsInstance(built, dm_filters.AND)
        self.assertEqual(
            ({"name": dm_filters.EQ("a")}, {"size": dm_filters.EQ(1)}),
            built.clauses,
        )

    def test_or_over_one_field_folds_into_in(self):
        # `= ANY(%s)` keeps the index that a chain of ORs may not.
        self.assertEqual(
            {"name": dm_filters.In(["a", "b"])},
            self._build("name = a OR name = b"),
        )

    def test_or_over_two_fields_stays_a_disjunction(self):
        built = self._build("name = a OR size = 1")

        self.assertIsInstance(built, dm_filters.OR)

    def test_or_of_something_other_than_equality_stays_a_disjunction(self):
        built = self._build("size > 1 OR size < 0")

        self.assertIsInstance(built, dm_filters.OR)

    def test_a_single_equality_is_not_folded(self):
        self.assertEqual({"name": dm_filters.EQ("a")}, self._build("name = a"))

    def test_or_of_has_is_contains_any(self):
        # The language has no `contains_any` operator and needs none: OR
        # of containment *is* overlap.
        self.assertEqual(
            {"tags": dm_filters.ContainsAny(["a", "b"])},
            self._build('tags:"a" OR tags:"b"'),
        )

    def test_and_of_has_is_one_wider_contains_all(self):
        self.assertEqual(
            {"tags": dm_filters.ContainsAll(["a", "b"])},
            self._build('tags:"a" AND tags:"b"'),
        )

    def test_a_single_has_stays_contains_all(self):
        self.assertEqual(
            {"tags": dm_filters.ContainsAll(["a"])}, self._build('tags:"a"')
        )

    def test_three_of_them_fold_together(self):
        self.assertEqual(
            {"tags": dm_filters.ContainsAny(["a", "b", "c"])},
            self._build('tags:"a" OR tags:"b" OR tags:"c"'),
        )

    def test_folding_is_partial(self):
        # The two array clauses merge; the third operand is left alone.
        built = self._build('tags:"a" OR tags:"b" OR name = x')

        self.assertIsInstance(built, dm_filters.OR)
        self.assertEqual(
            (
                {"tags": dm_filters.ContainsAny(["a", "b"])},
                {"name": dm_filters.EQ("x")},
            ),
            built.clauses,
        )

    def test_two_kinds_of_group_fold_side_by_side(self):
        built = self._build('name = a OR tags:"x" OR name = b OR tags:"y"')

        self.assertEqual(
            (
                {"name": dm_filters.In(["a", "b"])},
                {"tags": dm_filters.ContainsAny(["x", "y"])},
            ),
            built.clauses,
        )

    def test_an_implicit_and_folds_the_same_way(self):
        self.assertEqual(
            {"tags": dm_filters.ContainsAll(["a", "b"])},
            self._build('tags:"a" tags:"b"'),
        )

    def test_folding_does_not_cross_a_negation(self):
        built = self._build('tags:"a" OR NOT tags:"b"')

        self.assertIsInstance(built, dm_filters.OR)
        self.assertEqual({"tags": dm_filters.ContainsAll(["a"])}, built.clauses[0])
        self.assertIsInstance(built.clauses[1], dm_filters.NOT)

    def test_folding_does_not_cross_a_group(self):
        # `(a OR b) OR c` groups explicitly; the parenthesised part is one
        # operand and keeps its own shape.
        built = self._build('tags:"a" AND (tags:"b" OR tags:"c")')

        self.assertIsInstance(built, dm_filters.AND)
        self.assertEqual({"tags": dm_filters.ContainsAll(["a"])}, built.clauses[0])
        self.assertEqual({"tags": dm_filters.ContainsAny(["b", "c"])}, built.clauses[1])

    def test_a_wider_containment_does_not_fold_into_an_overlap(self):
        # `@> ARRAY[a,b]` is "holds both", and ORing it with `@> ARRAY[c]`
        # is not `&& ARRAY[a,b,c]`: the overlap lets a row holding only
        # `a` through, which the expression excludes.
        built = self._build('(tags:"a" AND tags:"b") OR tags:"c"')

        self.assertIsInstance(built, dm_filters.OR)
        self.assertEqual(
            (
                {"tags": dm_filters.ContainsAll(["a", "b"])},
                {"tags": dm_filters.ContainsAll(["c"])},
            ),
            built.clauses,
        )

    def test_the_singletons_around_a_wider_one_still_fold(self):
        # Folding stays partial: the group the wider clause cannot join is
        # still a group for the ones that can.
        built = self._build('tags:"a" OR (tags:"b" AND tags:"c") OR tags:"d"')

        self.assertEqual(
            (
                {"tags": dm_filters.ContainsAny(["a", "d"])},
                {"tags": dm_filters.ContainsAll(["b", "c"])},
            ),
            built.clauses,
        )

    def test_not_wraps_its_operand(self):
        built = self._build("NOT (name = a AND size = 1)")

        self.assertIsInstance(built, dm_filters.NOT)

    def test_every_leaf_holds_one_field(self):
        # Inside an OR a two-key mapping would flatten into two ORed
        # clauses instead of the AND it looks like.
        built = self._build("(name = a AND size = 1) OR name = b")

        for clause in built.clauses:
            if isinstance(clause, dict):
                self.assertEqual(1, len(clause))


class DialectGateTestCase(base.BaseTestCase):
    """A clause the dialect cannot compile is a 400, not a 500.

    Without the gate it reaches convert_filters and raises ValueError
    there, which the API layer has no reason to read as a client error.
    """

    def setUp(self):
        super().setUp()
        self._mysql = filter_lang.ModelFieldResolver(FilterModel, dialect="mysql")

    def test_array_containment_is_refused_on_mysql(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            filter_lang.compile_filter,
            'tags:"env:prod"',
            self._mysql,
        )

    def test_json_traversal_is_refused_on_mysql(self):
        self.assertRaises(
            ra_exc.ValidationFilterIncompatibleError,
            filter_lang.compile_filter,
            "spec.kind = totp",
            self._mysql,
        )

    def test_an_ordinary_comparison_still_works_on_mysql(self):
        built = filter_lang.compile_filter("size = 10", self._mysql)

        self.assertEqual({"size": dm_filters.EQ(10)}, built)

    def test_without_a_dialect_nothing_is_gated(self):
        resolver = filter_lang.ModelFieldResolver(FilterModel)

        self.assertIsInstance(
            filter_lang.compile_filter('tags:"env:prod"', resolver)["tags"],
            dm_filters.ContainsAll,
        )


class _PostgreSqlEngineFixture(mock.Mock):
    @property
    def dialect(self):
        dialect = mock.Mock()
        dialect.name = "postgresql"
        return dialect

    def escape(self, name):
        return f'"{name}"'


class _PostgreSqlSessionFixture(mock.Mock):
    @property
    def engine(self):
        return _PostgreSqlEngineFixture()

    @engine.setter
    def engine(self, value):
        pass


class SqlTestCase(base.BaseTestCase):
    """End to end: a filter string down to the SQL it compiles to."""

    def setUp(self):
        super().setUp()
        self._resolver = filter_lang.ModelFieldResolver(
            FilterModel, dialect="postgresql"
        )

    def _sql(self, text):
        return sql_filters.convert_filters(
            FilterModel,
            filter_lang.compile_filter(text, self._resolver),
            session=_PostgreSqlSessionFixture(),
        )

    def test_a_conjunction(self):
        self.assertEqual(
            '("name" = %s AND "size" > %s)',
            self._sql("name = a AND size > 1").construct_expression(),
        )

    def test_precedence_survives_the_compile(self):
        # Two clauses that do not fold into an In, so the OR stays visible.
        self.assertEqual(
            '(("name" = %s OR "name" <> %s) AND "size" > %s)',
            self._sql("name = a OR name != b AND size > 1").construct_expression(),
        )

    def test_negation_keeps_its_parentheses(self):
        # `NOT a AND b` and `NOT (a AND b)` are different filters. The
        # inner pair is the conjunction parenthesising itself; the outer
        # one is NOT's own, and only that one is load-bearing.
        self.assertEqual(
            'NOT (("name" = %s AND "size" > %s))',
            self._sql("NOT (name = a AND size > 1)").construct_expression(),
        )

    def test_negation_of_a_single_restriction(self):
        self.assertEqual(
            'NOT ("name" = %s)',
            self._sql("NOT name = a").construct_expression(),
        )

    def test_containment_reaches_the_array_operator(self):
        expression = self._sql('tags:"env:prod"')

        self.assertEqual('"tags" @> %s', expression.construct_expression())
        self.assertEqual([["env:prod"]], expression.value)

    def test_or_of_containment_is_one_overlap(self):
        # One `&&` probe, not two `@>` probes ORed together.
        expression = self._sql('tags:"env:prod" OR tags:"env:staging"')

        self.assertEqual('"tags" && %s', expression.construct_expression())
        self.assertEqual([["env:prod", "env:staging"]], expression.value)

    def test_and_of_containment_is_one_wider_containment(self):
        expression = self._sql('tags:"env:prod" AND tags:"region:eu"')

        self.assertEqual('"tags" @> %s', expression.construct_expression())
        self.assertEqual([["env:prod", "region:eu"]], expression.value)

    def test_a_wider_containment_stays_its_own_operator(self):
        expression = self._sql('(tags:"a" AND tags:"b") OR tags:"c"')

        self.assertEqual(
            '("tags" @> %s OR "tags" @> %s)',
            expression.construct_expression(),
        )
        self.assertEqual([["a", "b"], ["c"]], expression.value)

    def test_a_folded_or_is_one_any(self):
        expression = self._sql("name = a OR name = b")

        self.assertEqual('"name" = ANY(%s)', expression.construct_expression())
        self.assertEqual([["a", "b"]], expression.value)

    def test_traversal_extracts_the_json_key(self):
        self.assertEqual(
            "(\"spec\"->>'kind') = %s",
            self._sql("spec.kind = totp").construct_expression(),
        )

    def test_the_expression_cannot_escape_the_filters_it_is_anded_onto(self):
        # An OR inside the expression stays inside its own parentheses,
        # so a filter the caller never wrote -- a tenant scope, a parent
        # resource -- is not something an expression can OR its way past.
        expression = sql_filters.convert_filters(
            FilterModel,
            dm_filters.AND(
                {"uuid": dm_filters.EQ("11111111-1111-1111-1111-111111111111")},
                filter_lang.compile_filter("name = a OR size = 1", self._resolver),
            ),
            session=_PostgreSqlSessionFixture(),
        )

        self.assertEqual(
            '("uuid" = %s AND ("name" = %s OR "size" = %s))',
            expression.construct_expression(),
        )
