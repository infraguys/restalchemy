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

import six

from restalchemy.storage import base
from restalchemy.storage.sql.dialect.query_builder import common
from restalchemy.storage.sql import filters as sql_filters
from restalchemy.storage.sql import utils


class Table(common.AbstractClause):

    def __init__(self, model):
        self._name = model.__tablename__
        self._model = model
        self._columns = self._build_columns(self._model)
        super(Table, self).__init__()

    @property
    def name(self):
        return self._name

    @property
    def model(self):
        return self._model

    @staticmethod
    def _build_columns(model):
        # Note(efrolov): to save ordering
        ordered_result = collections.OrderedDict()
        for name, prop in model.properties.properties.items():
            ordered_result[name] = common.Column(name, prop)
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
        return utils.escape(self._name)


class Limit(common.AbstractClause):

    def __init__(self, value):
        super(Limit, self).__init__()
        self._value = value

    def compile(self):
        return "LIMIT %d" % self._value


class For(common.AbstractClause):

    def __init__(self, share=False):
        super(For, self).__init__()
        self._is_share = share

    def compile(self):
        return "FOR %s" % ("SHARE" if self._is_share else "UPDATE")


@six.add_metaclass(abc.ABCMeta)
class Criteria(common.AbstractClause):

    def __init__(self, clause1, clause2):
        super(Criteria, self).__init__()
        self._clause1 = clause1
        self._clause2 = clause2


class EQCriteria(Criteria):

    def compile(self):
        return "%s = %s" % (
            self._clause1.original.compile(),
            self._clause2.original.compile(),
        )


class On(common.AbstractClause):

    def __init__(self, list_of_criteria):
        super(On, self).__init__()
        self._list_of_criteria = list_of_criteria

    def compile(self):
        return " AND ".join([c.compile() for c in self._list_of_criteria])


class LeftJoin(common.AbstractClause):

    def __init__(self, table, on):
        # type: (common.TableAlias, On) -> LeftJoin
        super(LeftJoin, self).__init__()
        self._table = table
        self._on = on

    def compile(self):
        return "LEFT JOIN %s ON (%s)" % (
            self._table.compile(),
            self._on.compile(),
        )


class OrderByValue(common.AbstractClause):
    SORT_TYPES = frozenset(("ASC", "DESC"))

    def __init__(self, column, sort_type=None):
        super(OrderByValue, self).__init__()
        self._column = column
        if not sort_type:
            self._sort_type = "ASC"
        else:
            self._sort_type = sort_type.upper()
            if self._sort_type not in self.SORT_TYPES:
                raise ValueError("Unknown order: %s" % self._sort_type)

    def compile(self):
        return "%s %s" % (utils.escape(self._column.name), self._sort_type)


class ResultField(object):

    def __init__(self, alias_name):
        super(ResultField, self).__init__()
        self._alias_name = alias_name

    def parse(self, row):
        return row[self._alias_name]


class ResultNode(object):

    def __init__(self):
        super(ResultNode, self).__init__()
        self._child_nodes = {}

    def add_child_field(self, name, alias_name):
        self._child_nodes[name] = ResultField(alias_name=alias_name)
        return self._child_nodes[name]

    def add_child_node(self, name):
        self._child_nodes[name] = ResultNode()
        return self._child_nodes[name]

    def parse(self, row):
        result = base.PrefetchResult()
        for name, child_node in self._child_nodes.items():
            result[name] = child_node.parse(row)
        return result


class ResultParser(object):

    def __init__(self):
        super(ResultParser, self).__init__()
        self._root = ResultNode()

    @property
    def root(self):
        return self._root


class SelectQ(common.AbstractClause):

    def __init__(self, model):
        self._autoinc = 0
        self._autoinc_lock = threading.RLock()
        self._result_parser = ResultParser()
        self._model_table = common.TableAlias(
            Table(model),
            self._build_table_alias_name(),
        )
        self._select_expressions = []
        self._table_references = [self._model_table]  # type: list
        self._where_expression = sql_filters.AND()
        self._order_by_expressions = []
        self._for_expression = None
        self._limit_condition = None
        self._add_column_to_select_expressions(
            result_parser_node=self._result_parser.root,
            columns=self._model_table.get_columns(with_prefetch=False),
        )
        self._resolve_model_dependency(
            table=self._model_table,
            result_parser_node=self._result_parser.root,
        )
        super(SelectQ, self).__init__()

    def _resolve_model_dependency(self, table, result_parser_node):
        for column in table.get_prefetch_columns():
            dep_model = column.model_property.get_property_type()

            # Search primary key column
            id_properties = dep_model.get_id_property()
            if len(id_properties) != 1:
                msg = (
                    "Can't automatic resolve dependency for %s table"
                    " because the number of fields for primary keys (%r)"
                    " of model (%r) is not equal to 1."
                ) % (table.name, id_properties, dep_model)
                raise ValueError(msg)
            alias = common.TableAlias(
                Table(dep_model),
                self._build_table_alias_name(),
            )
            id_column = alias.get_column_by_name(list(id_properties.keys())[0])

            # Construct Left Join for prefetch dependency
            left_join = LeftJoin(
                table=alias, on=On([EQCriteria(column, id_column)])
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

    @staticmethod
    def _wrap_alias(table, fields):
        return [
            common.ColumnAlias(field, "%s_%s" % (table.name, field.name))
            for field in fields
        ]

    def where(self, filters=None):
        self._where_expression.extend_clauses(
            sql_filters.convert_filters(self._model_table, filters).clauses,
        )
        return self

    def limit(self, value):
        self._limit_condition = Limit(value)
        return self

    def for_(self, share=False):
        self._for_expression = For(share)
        return self

    def order_by(self, property_name, sort_type="ASC"):
        column = self._model_table.get_column_by_name(property_name)
        self._order_by_expressions.append(OrderByValue(column, sort_type))
        return self

    def _build_table_alias_name(self):
        return "t%d" % self._get_inc()

    def _get_inc(self):
        with self._autoinc_lock:
            self._autoinc += 1
            return self._autoinc

    def compile(self):
        # noinspection SqlInjection
        expression = "SELECT %s FROM %s" % (
            ", ".join([exp.compile() for exp in self._select_expressions]),
            " ".join([tbl.compile() for tbl in self._table_references]),
        )
        where_expressions = self._where_expression.construct_expression()
        if where_expressions:
            expression += " WHERE " + where_expressions
        if self._order_by_expressions:
            expression += " ORDER BY %s" % ", ".join(
                [exp.compile() for exp in self._order_by_expressions]
            )
        if self._limit_condition:
            expression += " %s" % self._limit_condition.compile()
        if self._for_expression:
            expression += " %s" % self._for_expression.compile()
        return expression

    def values(self):
        # TODO(efrolov): Must be read only list
        return self._where_expression.value

    def parse_row(self, row):
        return self._result_parser.root.parse(row)

    def parse_results(self, rows):
        return [self.parse_row(row) for row in rows]


class Q(object):

    @staticmethod
    def select(model):
        return SelectQ(model)
