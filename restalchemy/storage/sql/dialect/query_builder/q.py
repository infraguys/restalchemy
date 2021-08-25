# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import collections
import threading

from restalchemy.storage.sql.dialect import base
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
        for name, prop in model.properties.items():
            ordered_result[name] = common.Column(name, prop)
        return ordered_result

    def get_fields(self):
        return self._columns.values()

    def get_field_by_name(self, name):
        return self._columns[name]

    def compile(self):
        return utils.escape(self._name)


class Filter(common.AbstractClause):

    def __init__(self, filter, column):
        super(Filter, self).__init__()
        self._filter = filter
        self._column = column

    def compile(self):
        return self._filter.construct_expression(self._column.compile())


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
        return "FOR %s" % ('SHARE' if self._is_share else 'UPDATE')


class OrderByValue(common.AbstractClause):

    def __init__(self, column, sort_type=None):
        super(OrderByValue, self).__init__()
        self._column = column
        self._sort_type = sort_type or 'ASC'

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
        self._model_table = common.Alias(Table(model),
                                         self._build_table_alias_name())
        self._select_expressions = self._model_table.get_fields()
        self._table_references = [self._model_table]
        self._where_expression = sql_filters.AND()
        self._order_by_expressions = []
        self._for_expression = None
        self._limit_condition = None
        self._init_parser()
        super(SelectQ, self).__init__()

    def _init_parser(self):
        result_root_node = self._result_parser.root
        for column in self._select_expressions:
            result_root_node.add_child_field(column.original_name, column.name)

    @staticmethod
    def _wrap_alias(table, fields):
        return [common.Alias(field, "%s_%s" % (table.name, field.name))
                for field in fields]

    def where(self, filters=None):
        self._where_expression = sql_filters.convert_filters(
            self._model_table, filters)
        return self

    def limit(self, value):
        self._limit_condition = Limit(value)
        return self

    def for_(self, share=False):
        self._for_expression = For(share)
        return self

    def order_by(self, property_name, sort_type='ASC'):
        column = self._model_table.get_field_by_name(property_name)
        self._order_by_expressions.append(OrderByValue(column, sort_type))
        return self

    def _build_table_alias_name(self):
        return "t%d" % self._get_inc()

    def _get_inc(self):
        with self._autoinc_lock:
            self._autoinc += 1
            return self._autoinc

    def compile(self):
        expression = "SELECT %s FROM %s" % (
            ", ".join([exp.compile() for exp in self._select_expressions]),
            " ".join([tbl.compile() for tbl in self._table_references]),
        )
        where_expressions = self._where_expression.construct_expression()
        if where_expressions:
            expression += (
                " WHERE " + where_expressions)
        if self._order_by_expressions:
            expression += " ORDER BY %s" % ", ". join(
                [exp.compile() for exp in self._order_by_expressions]
            )
        if self._for_expression:
            expression += " %s" % self._for_expression.compile()
        if self._limit_condition:
            expression += " %s" % self._limit_condition.compile()
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
