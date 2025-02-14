#    Copyright 2021 George Melikov.
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

import six

from restalchemy.storage.sql import utils


@six.add_metaclass(abc.ABCMeta)
class AbstractClause(object):

    @abc.abstractmethod
    def compile(self):
        raise NotImplementedError()

    @property
    def original(self):
        return self


class BaseAlias(AbstractClause):

    def __init__(self, clause, name):
        super(BaseAlias, self).__init__()
        self._clause = clause
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def original_name(self):
        return self.original.name

    @property
    def original(self):
        return self._clause

    def compile(self):
        return "%s AS %s" % (self._clause.compile(), utils.escape(self.name))


class ColumnAlias(BaseAlias):

    @property
    def model_property(self):
        return self.original.model_property


class TableAlias(BaseAlias):

    def _wrap(self, column):
        return ColumnAlias(column, "%s_%s" % (self.name, column.name))

    def get_columns(self, with_prefetch=True, wrap_alias=True):
        return [
            self.get_column_by_name(col.name, wrap_alias)
            for col in self._clause.get_columns(with_prefetch)
        ]

    def get_prefetch_columns(self, wrap_alias=True):
        return [
            self.get_column_by_name(col.name, wrap_alias)
            for col in self._clause.get_prefetch_columns()
        ]

    def get_column_by_name(self, name, wrap_alias=True):
        result = ColumnFullPath(self, self._clause.get_column_by_name(name))
        return self._wrap(result) if wrap_alias else result


class Column(AbstractClause):

    def __init__(self, name, prop):
        self._name = name
        self._prop = prop
        super(Column, self).__init__()

    @property
    def name(self):
        return self._name

    @property
    def model_property(self):
        return self._prop

    @property
    def original_name(self):
        return self.name

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

    @property
    def model_property(self):
        return self._column.model_property

    @property
    def original_name(self):
        return self.name

    def compile(self):
        return "%s.%s" % (
            utils.escape(self._table.name),
            self._column.compile(),
        )
