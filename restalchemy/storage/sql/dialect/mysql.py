# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

from __future__ import absolute_import  # noqa

import abc

from mysql.connector import errors
import six

from restalchemy.storage.sql.dialect import base
from restalchemy.storage.sql.dialect import exceptions as exc
from restalchemy.storage.sql.dialect import query_builders
from restalchemy.storage.sql import filters as flt
from restalchemy.storage.sql import utils


@six.add_metaclass(abc.ABCMeta)
class AbstractProcessResult(base.AbstractProcessResult):

    def get_count(self):
        return self._result.rowcount

    @property
    def rows(self):
        return self.get_rows()

    @abc.abstractmethod
    def fetchall(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_rows(self):
        raise NotImplementedError()


class MySQLProcessResult(AbstractProcessResult):

    def __init__(self, result):
        super(MySQLProcessResult, self).__init__(result)
        self._rows = None

    def fetchall(self):
        for row in self._result:
            yield row

    def get_rows(self):
        if self._rows is None:
            self._rows = self._result.fetchall()
        return self._rows


class MySqlOrmProcessResult(AbstractProcessResult):

    def __init__(self, result, query):
        super(MySqlOrmProcessResult, self).__init__(result=result)
        self._query = query
        self._rows = None

    def fetchall(self):
        for row in self._result:
            yield self._query.parse_row(row)

    def get_rows(self):
        if self._rows is None:
            self._rows = self._query.parse_results(self._result.fetchall())
        return self._rows


@six.add_metaclass(abc.ABCMeta)
class AbstractDialectCommand(base.AbstractDialectCommand):

    def execute(self, session):
        try:
            return MySQLProcessResult(
                super(AbstractDialectCommand, self).execute(session))
        except errors.IntegrityError as e:
            if e.errno == 1062:
                raise exc.Conflict(code=e.sqlstate, message=e.msg)
            raise


class MySQLInsert(AbstractDialectCommand):

    def get_values(self):
        values = tuple()
        for column_name in self._table.get_column_names():
            values += (self._data[column_name],)
        return values

    def get_statement(self):
        column_names = self._table.get_escaped_column_names()
        return "INSERT INTO `%s` (%s) VALUES (%s)" % (
            self._table.name,
            ", ".join(column_names),
            ", ".join(['%s'] * len(column_names))
        )


class MySQLUpdate(AbstractDialectCommand):

    def __init__(self, table, ids, data):
        super(MySQLUpdate, self).__init__(table, data)
        self._ids = ids

    def get_values(self):
        values = tuple()
        column_names = self._table.get_column_names(with_pk=False)
        pk_names = self._table.get_pk_names()
        for column_name in column_names:
            values += (self._data[column_name],)
        for column_name in pk_names:
            values += (self._ids[column_name],)
        return values

    def get_statement(self):
        column_names = self._table.get_escaped_column_names(with_pk=False)
        pk_names = self._table.get_escaped_pk_names()
        return "UPDATE `%s` SET %s WHERE %s" % (
            self._table.name,
            ", ".join(["%s = %s" % (name, "%s") for name in column_names]),
            ", ".join(["%s = %s" % (name, "%s") for name in pk_names])
        )


class MySQLDelete(AbstractDialectCommand):

    def __init__(self, table, ids):
        super(MySQLDelete, self).__init__(table=table, data={})
        self._ids = ids

    def get_values(self):
        values = tuple()
        pk_names = self._table.get_pk_names()
        for column_name in pk_names:
            values += (self._ids[column_name],)
        return values

    def get_statement(self):
        pk_names = self._table.get_escaped_pk_names()
        return "DELETE FROM `%s` WHERE %s" % (
            self._table.name,
            ", ".join(["%s = %s" % (name, "%s") for name in pk_names])
        )


class MySQLBatchDelete(AbstractDialectCommand):

    def __init__(self, table, snapshot):
        super(MySQLBatchDelete, self).__init__(table=table, data={})
        self._snapshot = snapshot
        self._pk_keys = self._table.get_escaped_pk_names()
        keys_count = len(self._pk_keys)
        if keys_count == 1:
            self._is_multiple_primary_key = False
        elif keys_count > 1:
            self._is_multiple_primary_key = True
        else:
            raise ValueError("The model with table %r has 0 primary keys" %
                             table)

    def _get_values(self):
        values = []
        for snapshot in self._snapshot:
            for key in self._table.get_pk_names():
                values.append(snapshot[key])
        return values

    def _get_multiple_primary_key_values(self):
        return self._get_values()

    def _get_single_primary_key_values(self):
        # NOTE(efrolov): Wrap to list for `in` optimization
        return [self._get_multiple_primary_key_values()]

    def get_values(self):
        return (self._get_multiple_primary_key_values()
                if self._is_multiple_primary_key else
                self._get_single_primary_key_values())

    def _get_single_primary_key_statement(self):
        return "DELETE FROM `%s` WHERE %s in %s" % (
            self._table.name,
            self._pk_keys[0],
            "%s"
        )

    def _get_multiple_primary_key_statement(self):
        where_part = " AND ".join(
            [("%s = %s" % (key, '%s')) for key in self._pk_keys]
        )
        where_condition = " OR ".join(
            [where_part for _ in range(len(self._snapshot))]
        )
        return "DELETE FROM `%s` WHERE %s" % (
            self._table.name,
            where_condition,
        )

    def get_statement(self):
        return (self._get_multiple_primary_key_statement()
                if self._is_multiple_primary_key else
                self._get_single_primary_key_statement())


class MySQLBasicSelect(AbstractDialectCommand):
    def __init__(self, table, limit=None, order_by=None, locked=False):
        super(MySQLBasicSelect, self).__init__(table=table, data={})
        self._limit = limit
        self._order_by = order_by
        self._locked = locked

    def construct_limit(self):
        if self._limit:
            return " LIMIT " + str(self._limit)
        return ""

    def construct_locked(self):
        if self._locked:
            return " FOR UPDATE"
        return ""

    def construct_order_by(self):
        if self._order_by:
            res = []
            for name, sorttype in self._order_by.items():
                sorttype = sorttype.upper()
                if sorttype not in ['ASC', 'DESC', '', None]:
                    raise ValueError("Unknown order: %s." % sorttype)
                res.append('%s %s' % (utils.escape(name), sorttype or 'ASC'))
            return " ORDER BY " + ", ".join(res)
        return ""


class MySQLSelect(MySQLBasicSelect):

    def __init__(self, table, filters=None, limit=None,
                 order_by=None, locked=False):
        super(MySQLSelect, self).__init__(
            table=table, limit=limit, order_by=order_by, locked=locked)
        self._filters = filters or flt.AND()

    def get_values(self):
        return self._filters.value

    def construct_where(self):
        return self._filters.construct_expression()

    def get_statement(self):
        sql = "SELECT %s FROM `%s`" % (
            ", ".join(self._table.get_escaped_column_names()),
            self._table.name
        )
        filt = self.construct_where()

        return (sql + (" WHERE %s" % filt if filt else "")
                + self.construct_order_by()
                + self.construct_limit()
                + self.construct_locked())


class MySQLCustomSelect(MySQLBasicSelect):

    def __init__(self, table, where_conditions, where_values, limit=None,
                 order_by=None, locked=False):
        super(MySQLCustomSelect, self).__init__(
            table=table, limit=limit, order_by=order_by, locked=locked)
        self._where_conditions = where_conditions
        self._where_values = where_values

    def get_values(self):
        return self._where_values

    def construct_where(self):
        return self._where_conditions

    def get_statement(self):
        sql = "SELECT %s FROM `%s`" % (
            ", ".join(self._table.get_escaped_column_names()),
            self._table.name
        )
        return sql + " WHERE " + self.construct_where() \
            + self.construct_order_by() + self.construct_limit() \
            + self.construct_locked()


class MySQLCount(MySQLSelect):

    def __init__(self, table, filters=None):
        super(MySQLCount, self).__init__(table=table, filters=filters)

    def get_statement(self):
        sql = "SELECT COUNT(*) as COUNT FROM `%s`" % (
            self._table.name
        )
        filt = self.construct_where()

        return sql + (" WHERE %s" % filt if filt else "")


class MySqlOrmDialectCommand(base.AbstractDialectCommand):

    def __init__(self, table, query):
        super(MySqlOrmDialectCommand, self).__init__(table=table,
                                                     data=None)
        self._query = query

    def get_statement(self):
        return self._query.compile()

    def get_values(self):
        return self._query.values()

    def execute(self, session):
        try:
            return MySqlOrmProcessResult(
                result=super(MySqlOrmDialectCommand, self).execute(session),
                query=self._query,
            )
        except errors.IntegrityError as e:
            if e.errno == 1062:
                raise exc.Conflict(code=e.sqlstate, message=e.msg)
            raise


class MySqlOrm(object):

    @staticmethod
    def select(model):
        return query_builders.Q.select(model)


class MySQLDialect(base.AbstractDialect):

    def __init__(self):
        super(MySQLDialect, self).__init__()
        self._orm = MySqlOrm()

    @property
    def orm(self):
        return self._orm

    def orm_command(self, table, query):
        return MySqlOrmDialectCommand(table, query)

    def insert(self, table, data):
        return MySQLInsert(table, data)

    def update(self, table, ids, data):
        return MySQLUpdate(table, ids, data)

    def delete(self, table, ids):
        return MySQLDelete(table, ids)

    def select(self, table, filters, limit=None, order_by=None, locked=False):
        return MySQLSelect(table, filters, limit, order_by, locked)

    def custom_select(self, table, where_conditions, where_values, limit=None,
                      order_by=None, locked=False):
        return MySQLCustomSelect(table, where_conditions, where_values, limit,
                                 order_by, locked)

    def count(self, table, filters):
        return MySQLCount(table, filters)
