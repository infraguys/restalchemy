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

import abc
import collections
import threading

import six
import sortedcontainers

from restalchemy.storage.sql import utils


@six.add_metaclass(abc.ABCMeta)
class AbstractClause(object):

    @abc.abstractmethod
    def compile(self):
        raise NotImplementedError()


class Alias(AbstractClause):

    def __init__(self, clause, name):
        super(Alias, self).__init__()
        self._clause = clause
        self._name = name

    @property
    def name(self):
        return self._name

    def _wrap(self, column):
        return Alias(column, "%s_%s" % (self.name, column.name))

    def get_fields(self, wrap_alias=True):
        return [self.get_field_by_name(col.name, wrap_alias)
                for col in self._clause.get_fields()]

    def get_field_by_name(self, name, wrap_alias=True):
        result = ColumnFullPath(self, self._clause.get_field_by_name(name))
        return self._wrap(result) if wrap_alias else result

    def compile(self):
        return "%s AS %s" % (self._clause.compile(), utils.escape(self.name))


class Column(AbstractClause):

    def __init__(self, name, prop):
        self._name = name
        self._prop = prop
        super(Column, self).__init__()

    @property
    def name(self):
        return self._name

    def compile(self):
        return "%s" % (utils.escape(self._name))


class ColumnFullPath(AbstractClause):

    def __init__(self, table, column):
        super(ColumnFullPath, self).__init__()
        self._table = table
        self._column = column

    @property
    def name(self):
        return self._column.name

    def compile(self):
        return "%s.%s" % (utils.escape(self._table.name),
                          self._column.compile())


class Table(AbstractClause):

    def __init__(self, model):
        self._name = model.__tablename__
        self._model = model
        self._columns = self._build_columns(self._model)
        super(Table, self).__init__()

    @property
    def name(self):
        return self._name

    @staticmethod
    def _build_columns(model):
        # Note(efrolov): to save ordering
        ordered_result = collections.OrderedDict()
        for name, prop in model.properties.items():
            ordered_result[name] = Column(name, prop)
        return ordered_result

    def get_fields(self):
        return self._columns.values()

    def get_field_by_name(self, name):
        return self._columns[name]

    def compile(self):
        return utils.escape(self._name)


class Filter(AbstractClause):

    def __init__(self, filter, column):
        super(Filter, self).__init__()
        self._filter = filter
        self._column = column

    def compile(self):
        return self._filter.construct_expression(self._column.compile())


class Limit(AbstractClause):

    def __init__(self, value):
        super(Limit, self).__init__()
        self._value = value

    def compile(self):
        return "LIMIT %d" % self._value


class For(AbstractClause):

    def __init__(self, share=False):
        super(For, self).__init__()
        self._share = share

    def compile(self):
        return "FOR %s" % ('SHARE' if self._share else 'UPDATE')


class OrderByValue(AbstractClause):

    def __init__(self, column, sort_type=None):
        super(OrderByValue, self).__init__()
        self._column = column
        self._sort_type = sort_type or 'ASC'

    def compile(self):
        return "%s %s" % (utils.escape(self._column.name), self._sort_type)


class SelectQ(AbstractClause):

    def __init__(self, model):
        self._autoinc = 0
        self._autoinc_lock = threading.RLock()
        self._model_table = Alias(Table(model), self._build_table_alias_name())
        self._select_expressions = self._model_table.get_fields()
        self._table_references = [self._model_table]
        self._where_condition = []
        self._expression_values = []
        self._order_by_expressions = []
        self._for_expression = None
        self._limit_condition = None
        super(SelectQ, self).__init__()

    @staticmethod
    def _wrap_alias(table, fields):
        return [Alias(field, "%s_%s" % (table.name, field.name))
                for field in fields]

    def where(self, filters=None):
        # TODO(efrolov) Drop sorting here to performance
        filters = sortedcontainers.SortedDict(filters or {})
        for name, cause in filters.items():
            column = self._model_table.get_field_by_name(
                name, wrap_alias=False,
            )
            value = cause.value
            self._where_condition.append(Filter(cause, column))
            self._expression_values.append(value)
        return self

    def limit(self, value):
        self._limit_condition = Limit(value)
        return self

    def for_(self, share=False):
        self._for_expression = For(share)
        return self

    def order_by(self, column_name, sort_type='ASC'):
        column = self._model_table.get_field_by_name(column_name)
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
        if self._where_condition:
            expression += (
                " WHERE %s" % " AND ".join(
                    [exp.compile() for exp in self._where_condition]
                )
            )
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
        return self._expression_values


class Q(object):

    @staticmethod
    def select(model):
        return SelectQ(model)
