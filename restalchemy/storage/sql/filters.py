# Copyright 2018 Eugene Frolov <eugene@frolov.net.ru>
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

import abc
from collections import abc as collections_abc
import decimal
import logging

from restalchemy.dm import filters
from restalchemy.dm import types
from restalchemy.storage.sql.dialect.query_builder import common

LOG = logging.getLogger(__name__)


class AbstractClause(metaclass=abc.ABCMeta):
    def __init__(self, column, value_type, value, session):
        super(AbstractClause, self).__init__()
        self._value = self._convert_value(value_type, value)
        self._column = column
        self._session = session

    def _convert_value(self, value_type, value):
        return value_type.to_simple_type(value)

    @property
    def value(self):
        return self._value

    @property
    def column(self):
        return (
            self._column.compile()
            if isinstance(self._column, common.ColumnFullPath)
            else self._column
        )

    @abc.abstractmethod
    def construct_expression(self):
        raise NotImplementedError()


class EQ(AbstractClause):
    def construct_expression(self):
        return f"{self.column} = %s"


class NE(AbstractClause):
    def construct_expression(self):
        return f"{self.column} <> %s"


class GT(AbstractClause):
    def construct_expression(self):
        return f"{self.column} > %s"


class GE(AbstractClause):
    def construct_expression(self):
        return f"{self.column} >= %s"


class LT(AbstractClause):
    def construct_expression(self):
        return f"{self.column} < %s"


class LE(AbstractClause):
    def construct_expression(self):
        return f"{self.column} <= %s"


class Is(AbstractClause):
    def construct_expression(self):
        return f"{self.column} IS %s"


class IsNot(AbstractClause):
    def construct_expression(self):
        return f"{self.column} IS NOT %s"


class In(AbstractClause):
    def _convert_value(self, value_type, value):
        # Note(efrolov): Replace empty list with [Null]. Some SQL servers
        #                forbid empty lists in "in" operator.
        return [value_type.to_simple_type(item) for item in value] or [None]


class MySqlIn(In):
    def construct_expression(self):
        return f"{self.column} IN %s"


class PostgreSqlIn(In):
    def construct_expression(self):
        return f"{self.column} = ANY(%s)"


class MySqlNotIn(In):
    def construct_expression(self):
        return f"{self.column} NOT IN %s"


class PostgreSqlNotIn(In):
    def construct_expression(self):
        # Use NOT (= ANY(...)), not != ANY(...): in PostgreSQL, expr != ANY(arr)
        # is true if expr differs from *any* array element (OR of !=), not NOT IN.
        return f"NOT ({self.column} = ANY(%s))"


class PostgreSqlIs(Is):
    def construct_expression(self):
        return f"{self.column} IS NOT DISTINCT FROM (%s)"


class PostgreSqlIsNot(IsNot):
    def construct_expression(self):
        return f"{self.column} IS DISTINCT FROM (%s)"


class Like(AbstractClause):
    def construct_expression(self):
        return ("%s LIKE " % self.column) + "%s"


class NotLike(AbstractClause):
    def construct_expression(self):
        return ("%s NOT LIKE " % self.column) + "%s"


class PostgreSqlContainsAll(AbstractClause):
    """Array @>: column contains all elements of the given array."""

    def construct_expression(self):
        return f"{self.column} @> %s"


class PostgreSqlContainsAny(AbstractClause):
    """Array &&: column overlaps with (shares at least one element of) the given array."""

    def construct_expression(self):
        return f"{self.column} && %s"


class AbstractExpression(metaclass=abc.ABCMeta):
    def __init__(self, *clauses):
        super(AbstractExpression, self).__init__()
        self._clauses = clauses

    def extend_clauses(self, clauses):
        self._clauses = self._clauses + clauses

    @property
    def clauses(self):
        return self._clauses

    @property
    def value(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def construct_expression(self):
        raise NotImplementedError()


class ClauseList(AbstractExpression):
    @property
    def value(self):
        res = []
        for val in self._clauses:
            if isinstance(val, AbstractExpression):
                res.extend(val.value)
            else:
                res.append(val.value)
        return res

    @property
    def operator(self):
        raise NotImplementedError

    def construct_expression(self):
        clause_count = len(self._clauses)

        if clause_count == 0:
            return ""

        if clause_count == 1:
            return self._clauses[0].construct_expression()

        joined = f" {self.operator} ".join(
            clause.construct_expression() for clause in self._clauses
        )
        return f"({joined})"


class AND(ClauseList):
    operator = "AND"


class OR(ClauseList):
    operator = "OR"


# Casts applied when comparing a value pulled out of jsonb via ->> (which
# always yields text or SQL NULL). Keys not listed here (str, None) are
# compared as-is against the extracted text. This mapping is part of the
# public contract of PostgreSqlJSONFields: an expression index must use the
# *exact same* cast, or Postgres will silently ignore it and fall back to a
# seq scan.
_JSON_SCALAR_CASTS = {
    bool: "boolean",
    int: "bigint",
    float: "double precision",
    decimal.Decimal: "numeric",
}


class _JSONFieldClause(AbstractExpression):
    """One `(column->>'key') [::cast] OP %s` comparison for a JSONFields key.

    The key is inlined into the SQL text as an escaped string literal
    (quotes doubled, never bound as a parameter): PostgreSQL only matches a
    query expression against an expression index (e.g. `(spec->>'kind')`)
    when the two are syntactically identical, and once a prepared
    statement graduates to a *generic* plan (by default, after 5
    executions) it no longer has a concrete parameter value to compare --
    a bound `%s` for the key would silently stop using the index from
    then on. Only the comparison value is a bound parameter.
    """

    _OPERATORS = {
        filters.EQ: "=",
        filters.NE: "<>",
        filters.GT: ">",
        filters.GE: ">=",
        filters.LT: "<",
        filters.LE: "<=",
        filters.Like: "LIKE",
        filters.NotLike: "NOT LIKE",
        filters.Is: "IS NOT DISTINCT FROM",
        filters.IsNot: "IS DISTINCT FROM",
    }

    def __init__(self, column_sql, key, clause_type, raw_value, cast):
        if clause_type not in self._OPERATORS:
            raise ValueError(
                "JSONFields does not support clause %s for key %r" % (clause_type, key)
            )
        self._column_sql = column_sql
        self._key = key
        self._clause_type = clause_type
        self._raw_value = raw_value
        self._cast = cast

    @property
    def value(self):
        return [self._raw_value]

    def construct_expression(self):
        escaped_key = self._key.replace("'", "''")
        path = f"({self._column_sql}->>'{escaped_key}')"
        if self._cast:
            path = f"{path}::{self._cast}"
        return f"{path} {self._OPERATORS[self._clause_type]} %s"


class PostgreSqlJSONFields(ClauseList):
    """AND of per-key comparisons against paths inside a jsonb column.

    Compiles ``JSONFields({"kind": "foo", "value": GT(10)})`` on column
    ``spec`` to roughly
    ``(spec->>'kind') = %s AND (spec->>'value')::bigint > %s`` -- per-key
    ``->>`` extraction (+ cast where the value isn't text), not a single
    ``@>`` containment check. That's what lets it express ranges
    (GT/GE/LT/LE), not just equality.

    Indexing recipe for a "kind" column (verified with EXPLAIN ANALYZE
    against a 2M-row jsonb table, see restalchemy issue #133):

    This clause is meant for the common polymorphic-JSON shape where a
    column always carries a discriminator key (conventionally "kind") plus
    a handful of extra keys whose *presence and meaning are private to that
    kind* -- e.g. ``{"kind": "totp", "period": 30}`` vs.
    ``{"kind": "yubiotp", "device_id": "..."}`` in the same column. Two
    different index shapes are needed, for two different query shapes:

      1. **Always add one plain expression index on the discriminator
         itself**, regardless of what else you index -- it's what every
         query touching this column filters by first, it's the same for
         every kind, and it's cheap (one text value per row)::

             CREATE INDEX ix_t_spec_kind ON t ((spec->>'kind'));

      2. **For each (kind, field) pair you actually query by, add a
         *partial* expression index scoped to that kind** -- not a
         table-wide index on the field name. Because the field's meaning
         (and its presence at all) is specific to one kind, a table-wide
         index would carry rows from every other kind for nothing, and
         still couldn't be reused across kinds since the cast may differ
         per kind too::

             CREATE INDEX ix_t_spec_totp_period ON t (((spec->>'period')::bigint))
                 WHERE spec->>'kind' = 'totp';

         In testing, a query combining the discriminator with a per-kind
         field (``kind = 'foo' AND value > 10``) was ~2x faster with this
         partial index than with only the plain discriminator index from
         (1), and a pure discriminator-only query against a *single* partial
         index (no other predicate) served as an index-only scan ~9x faster
         than the plain discriminator index -- Postgres can use a partial
         index's own WHERE clause as proof of the predicate, no extra
         condition needed. If you filter by more than one field of the same
         kind together, put them in one composite partial index rather than
         one index per field::

             CREATE INDEX ix_t_spec_totp_period_active
                 ON t (((spec->>'period')::bigint), (spec->>'active'))
                 WHERE spec->>'kind' = 'totp';

      Do **not** build a partial index for every (kind, field) combination
      that merely *exists* in the schema -- each one is pure write overhead
      until a query actually needs it. Add them lazily, driven by real
      query patterns, the same way you'd add any other index.

      * The cast in the index must match ``_JSON_SCALAR_CASTS`` exactly
        (e.g. ``::bigint`` for a Python ``int``) -- Postgres only uses an
        expression index when the query expression is syntactically
        identical to the index definition, casts included. A cast mismatch
        doesn't error, it just silently falls back to a seq/bitmap scan of
        the whole column -- this bit us during testing (a hand-written
        ``::int`` index was ignored by a query compiled with ``::bigint``).

      * A GIN index (``USING gin(spec)`` / ``gin(spec jsonb_path_ops)``)
        does NOT speed up anything generated here: GIN accelerates
        ``@>``/``?``/``?|``/``?&``, not ``->>`` comparisons, and in testing
        was sometimes *slower* than a plain seq scan at moderate (~20%)
        selectivity. Only add GIN if something else in the app genuinely
        queries with raw containment -- it also isn't free on writes:
        pending-list flushes add write-latency spikes on jsonb columns that
        are updated often.

      * ``->>`` returns SQL NULL both when the key is absent and when its
        JSON value is JSON ``null``; ``Is``/``IsNot`` (and ``EQ``/``NE``
        with a ``None`` value, downgraded to them below for the same
        NULL-safety reason as the top-level filters) can't tell these
        apart.
    """

    operator = "AND"

    def __init__(self, column, value_type, value, session):
        column_sql = (
            column.compile() if isinstance(column, common.ColumnFullPath) else column
        )
        clauses = []
        for key, clause in value.items():
            raw_value = clause.value
            clause_type = type(clause)
            if raw_value is None and clause_type in (filters.EQ, filters.NE):
                clause_type = filters.Is if clause_type is filters.EQ else filters.IsNot
            cast = _JSON_SCALAR_CASTS.get(type(raw_value))
            clauses.append(
                _JSONFieldClause(column_sql, key, clause_type, raw_value, cast)
            )
        super().__init__(*clauses)


FILTER_MAPPING = {
    "mysql": {
        filters.EQ: EQ,
        filters.NE: NE,
        filters.GT: GT,
        filters.GE: GE,
        filters.LE: LE,
        filters.LT: LT,
        filters.Is: Is,
        filters.IsNot: IsNot,
        filters.In: MySqlIn,
        filters.NotIn: MySqlNotIn,
        filters.Like: Like,
        filters.NotLike: NotLike,
    },
    "postgresql": {
        filters.EQ: EQ,
        filters.NE: NE,
        filters.GT: GT,
        filters.GE: GE,
        filters.LE: LE,
        filters.LT: LT,
        filters.Is: PostgreSqlIs,
        filters.IsNot: PostgreSqlIsNot,
        filters.In: PostgreSqlIn,
        filters.NotIn: PostgreSqlNotIn,
        filters.Like: Like,
        filters.NotLike: NotLike,
        filters.ContainsAll: PostgreSqlContainsAll,
        filters.ContainsAny: PostgreSqlContainsAny,
        filters.JSONFields: PostgreSqlJSONFields,
    },
}

FILTER_EXPR_MAPPING = {
    filters.AND: AND,
    filters.OR: OR,
}


class AsIsType(types.BaseType):
    def validate(self, value):
        return True

    def to_simple_type(self, value):
        return value

    def from_simple_type(self, value):
        return value

    def from_unicode(self, value):
        return value


def convert_filters(model, filters_root, session):
    filters_root = filters_root or filters.AND()
    if isinstance(filters_root, filters.AbstractExpression):
        return iterate_filters(model, filters_root, session=session)
    return iterate_filters(
        model,
        filters.AND(filters_root),
        session=session,
    )


def iterate_filters(model, filter_list, session):
    # Just expression
    if isinstance(filter_list, filters.AbstractExpression):
        clauses = iterate_filters(model, filter_list.clauses, session)
        return FILTER_EXPR_MAPPING[type(filter_list)](*clauses)

    # Tuple of causes from expression
    if isinstance(filter_list, tuple):
        clauses = []
        for cause in filter_list:
            c_causes = iterate_filters(model, cause, session)
            if isinstance(cause, filters.AbstractExpression):
                clauses.append(c_causes)
            else:
                clauses.extend(c_causes)
        return clauses

    # old style mappings (dict, multidict)
    if isinstance(filter_list, collections_abc.Mapping):
        clauses = []
        for name, filt in filter_list.items():
            if isinstance(model, common.TableAlias):
                value_type = (
                    model.original.model.properties.properties[name].get_property_type()
                ) or AsIsType()
                column = model.get_column_by_name(
                    name,
                    wrap_alias=False,
                )
            else:
                value_type = (
                    model.properties.properties[name].get_property_type()
                ) or AsIsType()
                column = session.engine.escape(name)
            # Make API compatible with previous versions.
            if not isinstance(filt, filters.AbstractClause):
                LOG.warning(
                    "DEPRECATED: pleases use %s wrapper for filter value",
                    filters.EQ,
                )
                clauses.append(EQ(column, value_type, filt, session=session))
                continue

            try:
                clauses.append(
                    FILTER_MAPPING[session.engine.dialect.name][type(filt)](
                        column,
                        value_type,
                        filt.value,
                        session=session,
                    ),
                )
            except KeyError:
                raise ValueError(
                    "Can't convert API filter to SQL storage "
                    "filter. Unknown filter %s" % filt
                )
        return clauses

    raise ValueError("Unknown type of filters: %s" % filter_list)
