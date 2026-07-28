#    Copyright 2021 Eugene Frolov.
#
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
import collections
import threading
import weakref

from restalchemy.dm import properties as ra_properties
from restalchemy.storage import base
from restalchemy.storage.sql import filters as sql_filters
from restalchemy.storage.sql.dialect.query_builder import common


class Table(common.AbstractClause):
    def __init__(self, model, session):
        super().__init__(session)
        self._name = model.__tablename__
        self._model = model
        self._columns = self._build_columns(self._model)

    @property
    def name(self):
        return self._name

    @property
    def model(self):
        return self._model

    def _build_columns(self, model):
        # Note(efrolov): to save ordering
        ordered_result = collections.OrderedDict()
        for name, prop in model.properties.properties.items():
            ordered_result[name] = common.Column(name, prop, self._session)
        return ordered_result

    def get_columns(self, with_prefetch=True):
        return [
            column
            for column in self._columns.values()
            if not column.model_property.is_prefetch() or with_prefetch
        ]

    def get_prefetch_columns(self):
        return [
            column
            for column in self._columns.values()
            if column.model_property.is_prefetch()
        ]

    def get_column_by_name(self, name):
        return self._columns[name]

    def compile(self):
        return self._session.engine.escape(self._name)


class Limit(common.AbstractClause):
    def __init__(self, value, session):
        super().__init__(session)
        self._value = value

    def compile(self):
        return f"LIMIT {self._value}"


class For(common.AbstractClause):
    def __init__(self, session, share=False):
        super().__init__(session)
        self._is_share = share

    def compile(self):
        return "FOR %s" % ("SHARE" if self._is_share else "UPDATE")


class Criteria(common.AbstractClause, metaclass=abc.ABCMeta):
    def __init__(self, clause1, clause2, session):
        super().__init__(session)
        self._clause1 = clause1
        self._clause2 = clause2


class EQCriteria(Criteria):
    def compile(self):
        return (
            f"{self._clause1.original.compile()} = {self._clause2.original.compile()}"
        )


class On(common.AbstractClause):
    def __init__(self, list_of_criteria, session):
        super().__init__(session)
        self._list_of_criteria = list_of_criteria

    def compile(self):
        return " AND ".join([c.compile() for c in self._list_of_criteria])


class LeftJoin(common.AbstractClause):
    def __init__(self, table, on, session):
        # type: (common.TableAlias, On) -> LeftJoin
        super().__init__(session)
        self._table = table
        self._on = on

    def compile(self):
        return f"LEFT JOIN {self._table.compile()} ON ({self._on.compile()})"


class OrderByValue(common.AbstractClause):
    SORT_TYPES = frozenset(
        (
            "ASC",
            "ASC NULLS FIRST",
            "ASC NULLS LAST",
            "DESC",
            "DESC NULLS FIRST",
            "DESC NULLS LAST",
        )
    )

    def __init__(self, column, session, sort_type=None):
        super().__init__(session)
        self._column = column
        if not sort_type:
            self._sort_type = "ASC"
        else:
            self._sort_type = sort_type.upper()
            if self._sort_type not in self.SORT_TYPES:
                raise ValueError(f"Unknown order: {self._sort_type}")

    def compile(self):
        """
        Generic compilation of the ORDER BY clause.

        A note regarding "NULLS FIRST/LAST":
            Resulting SQL looks like:
                ORDER BY
                    CASE WHEN table.col IS NULL THEN 0 ELSE 1 END ASC,
                    table.col ASC

            So, for example with NULLS FIRST:
            CASE result | Actual value
            ----------- | ------------
             0          | NULL
             0          | NULL
             1          | 2
             1          | 5
             1          | 8

            This approach is generic, and works for both PostgreSQL and MySQL,
            unlike PostgreSQL-specific "NULLS FIRST/LAST".

            todo: Add PostgreSQL-specific ordering using the native
                NULLS FIRST/LAST syntax for its performance benefits.
        """
        column_name = self._column.compile()

        # Handle simple ASC/DESC without NULLS specification
        if self._sort_type in ("ASC", "DESC"):
            return f"{column_name} {self._sort_type}"

        # Handle NULLS FIRST/LAST with a generic CASE approach
        order_map = {
            "ASC NULLS FIRST": ("ASC", 0, 1),
            "ASC NULLS LAST": ("ASC", 1, 0),
            "DESC NULLS FIRST": ("DESC", 0, 1),
            "DESC NULLS LAST": ("DESC", 1, 0),
        }
        order, then_, else_ = order_map[self._sort_type]
        return (
            f"CASE WHEN {column_name} IS NULL "
            f"THEN {then_} ELSE {else_} END ASC, "
            f"{column_name} {order}"
        )


class ResultField:
    def __init__(self, alias_name):
        super().__init__()
        self._alias_name = alias_name

    def parse(self, row):
        return row[self._alias_name]


class ResultNode:
    def __init__(self):
        super().__init__()
        self._child_nodes = {}
        # The names this node reads straight out of the row, as
        # (name, alias) pairs -- everything but a nested node, which has a
        # row of its own to walk. A model without prefetched relationships
        # is entirely flat, and then parsing a row is one loop instead of
        # a call per column per row.
        self._flat_fields = []
        # Whether the row already reads as the mapping this node stands
        # for: nothing nested, and every column under its own name.
        self._verbatim = True

    def add_child_field(self, name, alias_name):
        self._child_nodes[name] = ResultField(alias_name=alias_name)
        self._flat_fields.append((name, alias_name))
        self._verbatim = self._verbatim and name == alias_name
        return self._child_nodes[name]

    def add_child_node(self, name):
        self._child_nodes[name] = ResultNode()
        self._flat_fields = [field for field in self._flat_fields if field[0] != name]
        self._verbatim = False
        return self._child_nodes[name]

    def parse(self, row):
        if self._verbatim:
            # The row is the mapping already -- which is what selecting
            # without aliases is for. Both drivers build a row of their
            # own per row, so it is the caller's to keep.
            return row
        result = base.PrefetchResult()
        if len(self._flat_fields) == len(self._child_nodes):
            for name, alias_name in self._flat_fields:
                result[name] = row[alias_name]
            return result
        for name, child_node in self._child_nodes.items():
            result[name] = child_node.parse(row)
        return result


class ResultParser:
    def __init__(self):
        super().__init__()
        self._root = ResultNode()

    @property
    def root(self):
        return self._root


class _EngineSession(object):
    """Stands in for a session where only the engine is ever asked for.

    Everything a `SELECT` builds out of a model -- tables, columns,
    aliases -- reads one thing off the session it is handed: how the
    engine escapes a name. Holding a real session in a structure that
    outlives the request would pin a connection to it; this holds the
    engine and nothing else.
    """

    __slots__ = ("_engine", "__weakref__")

    def __init__(self, engine):
        # Weakly: what is built from an engine is kept under that engine
        # in a weak map, and a strong reference from the value back to
        # the key would keep every engine ever queried alive -- with its
        # connections, which are closed when it is collected.
        self._engine = weakref.ref(engine)

    @property
    def engine(self):
        return self._engine()


class _SelectShape(object):
    """The part of a `SELECT` that a model and an engine already decide.

    Which columns are selected, under which aliases, from which tables,
    and how a row of them maps back onto the model: none of it depends on
    the filters, the ordering or the limit, and all of it was rebuilt --
    an object per column, three deep -- per query. It is built once per
    model per engine and read from there.

    Read-only once built: a query appends only to lists of its own.
    """

    __slots__ = (
        "model_table",
        "select_expressions",
        "table_references",
        "result_parser",
        "prefix",
    )

    def __init__(
        self,
        model_table,
        select_expressions,
        table_references,
        result_parser,
        prefix,
    ):
        self.model_table = model_table
        self.select_expressions = select_expressions
        self.table_references = table_references
        self.result_parser = result_parser
        self.prefix = prefix


# Per engine, per model. Weak on the engine so that a short-lived one --
# a test builds them freely -- is not kept alive by having been queried.
_SHAPE_CACHE = weakref.WeakKeyDictionary()
_SHAPE_CACHE_LOCK = threading.Lock()

# The declaration these shapes were built from. A model's properties can
# be reordered after a query has run (`sort_properties()` does that), and
# then nothing built from the old order is worth keeping.
_SHAPE_CACHE_VERSION = ra_properties.declaration_version


def clear_shape_cache():
    """Forget what models looked like when they were last queried."""
    with _SHAPE_CACHE_LOCK:
        _SHAPE_CACHE.clear()


class SelectQ(common.AbstractClause):
    def __init__(self, model, session):
        super().__init__(session)
        # What the shape refers to weakly, a query being built refers to
        # strongly: the engine has to outlive the compile it is part of.
        self._engine = session.engine
        shape = self._get_shape(model, session)
        self._model_table = shape.model_table
        self._select_expressions = shape.select_expressions
        self._table_references = shape.table_references
        self._result_parser = shape.result_parser
        self._prefix = shape.prefix
        self._where_expression = sql_filters.AND()
        self._order_by_expressions = []
        self._for_expression = None
        self._limit_condition = None

    @classmethod
    def _get_shape(cls, model, session):
        global _SHAPE_CACHE_VERSION

        engine = session.engine
        if _SHAPE_CACHE_VERSION == ra_properties.declaration_version:
            shapes = _SHAPE_CACHE.get(engine)
            if shapes is not None:
                shape = shapes.get(model)
                if shape is not None:
                    return shape
        else:
            clear_shape_cache()
            _SHAPE_CACHE_VERSION = ra_properties.declaration_version
        with _SHAPE_CACHE_LOCK:
            shapes = _SHAPE_CACHE.setdefault(engine, {})
            shape = shapes.get(model)
            if shape is None:
                shape = cls._build_shape(model, engine)
                shapes[model] = shape
        return shape

    @classmethod
    def _build_shape(cls, model, engine):
        builder = cls.__new__(cls)
        common.AbstractClause.__init__(builder, _EngineSession(engine))
        builder._autoinc = 0
        builder._autoinc_lock = threading.RLock()
        builder._result_parser = ResultParser()
        builder._model_table = common.TableAlias(
            Table(model, session=builder._session),
            builder._build_table_alias_name(),
            session=builder._session,
        )
        builder._select_expressions = []
        builder._table_references = [builder._model_table]
        # A column is aliased so that two tables can both select one; a
        # model without prefetched relationships is selected from one
        # table, and then the alias only renames a row on its way back.
        joins = bool(builder._model_table.get_prefetch_columns(wrap_alias=False))
        builder._add_column_to_select_expressions(
            result_parser_node=builder._result_parser.root,
            columns=builder._model_table.get_columns(
                with_prefetch=False,
                wrap_alias=joins,
            ),
        )
        builder._resolve_model_dependency(
            table=builder._model_table,
            result_parser_node=builder._result_parser.root,
        )
        return _SelectShape(
            model_table=builder._model_table,
            select_expressions=builder._select_expressions,
            table_references=builder._table_references,
            result_parser=builder._result_parser,
            prefix="SELECT %s FROM %s"
            % (
                ", ".join([exp.compile() for exp in builder._select_expressions]),
                " ".join([tbl.compile() for tbl in builder._table_references]),
            ),
        )

    def _resolve_model_dependency(self, table, result_parser_node):
        for column in table.get_prefetch_columns():
            dep_model = column.model_property.get_property_type()

            # Search primary key column
            id_properties = dep_model.get_id_property()
            if len(id_properties) != 1:
                msg = (
                    f"Can't automatic resolve dependency for {table.name} table"
                    f" because the number of fields for primary keys ({id_properties!r})"
                    f" of model ({dep_model!r}) is not equal to 1."
                )
                raise ValueError(msg)
            alias = common.TableAlias(
                Table(dep_model, session=self._session),
                self._build_table_alias_name(),
                session=self._session,
            )
            id_column = alias.get_column_by_name(next(iter(id_properties.keys())))

            # Construct Left Join for prefetch dependency
            left_join = LeftJoin(
                table=alias,
                on=On(
                    [EQCriteria(column, id_column, session=self._session)],
                    session=self._session,
                ),
                session=self._session,
            )
            self._table_references.append(left_join)

            # Adding columns to fetch data on it
            node = result_parser_node.add_child_node(column.original_name)
            self._add_column_to_select_expressions(
                result_parser_node=node,
                columns=alias.get_columns(with_prefetch=False),
            )

            # Processing parent model to resolve dependencies
            self._resolve_model_dependency(
                table=alias,
                result_parser_node=node,
            )

    def _add_column_to_select_expressions(self, result_parser_node, columns):
        for column in columns:
            result_parser_node.add_child_field(
                column.original_name,
                column.name,
            )
            self._select_expressions.append(column)
        return self._select_expressions

    def _wrap_alias(self, table, fields):
        return [
            common.ColumnAlias(
                field,
                f"{table.name}_{field.name}",
                session=self._session,
            )
            for field in fields
        ]

    def where(self, filters=None):
        filters_converted = sql_filters.convert_filters(
            self._model_table,
            filters,
            session=self._session,
        )
        filters_tuple = (filters_converted,)
        self._where_expression.extend_clauses(filters_tuple)
        return self

    def limit(self, value):
        self._limit_condition = Limit(
            value,
            session=self._session,
        )
        return self

    def for_(self, share=False):
        self._for_expression = For(share)
        return self

    def order_by(self, property_name, sort_type="ASC"):
        column = self._model_table.get_column_by_name(
            property_name,
            wrap_alias=False,
        )

        self._order_by_expressions.append(
            OrderByValue(
                column=column,
                sort_type=sort_type,
                session=self._session,
            )
        )
        return self

    def _build_table_alias_name(self):
        return f"t{self._get_inc()}"

    def _get_inc(self):
        with self._autoinc_lock:
            self._autoinc += 1
            return self._autoinc

    def compile(self):
        # noinspection SqlInjection
        expression = self._prefix
        where_expressions = self._where_expression.construct_expression()
        if where_expressions:
            expression += " WHERE " + where_expressions
        if self._order_by_expressions:
            expression += " ORDER BY {}".format(
                ", ".join([exp.compile() for exp in self._order_by_expressions])
            )
        if self._limit_condition:
            expression += f" {self._limit_condition.compile()}"
        if self._for_expression:
            expression += f" {self._for_expression.compile()}"
        return expression

    def values(self):
        # TODO(efrolov): Must be read only list
        return self._where_expression.value

    def parse_row(self, row):
        return self._result_parser.root.parse(row)

    def parse_results(self, rows):
        return [self.parse_row(row) for row in rows]


class Q:
    @staticmethod
    def select(model, session):
        return SelectQ(model, session)
