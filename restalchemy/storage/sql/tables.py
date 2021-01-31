# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2020 Eugene Frolov.
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

from restalchemy.storage.sql import utils


class SQLTable(object):

    def __init__(self, table_name, model):
        super(SQLTable, self).__init__()
        self._table_name = table_name
        self._model = model

    def get_column_names(self, with_pk=True, do_sort=True):
        result = []
        for name, prop in self._model.properties.items():
            if not with_pk and prop.is_id_property():
                continue
            result.append(name)
        if do_sort:
            result.sort()
        return result

    def get_escaped_column_names(self, with_pk=True, do_sort=True):
        return [utils.escape(column_name) for column_name in
                self.get_column_names(with_pk=with_pk, do_sort=do_sort)]

    def get_pk_names(self, do_sort=True):
        result = []
        for name, prop in self._model.properties.items():
            if prop.is_id_property():
                result.append(name)
        if do_sort:
            result.sort()
        return result

    def get_escaped_pk_names(self, do_sort=True):
        return [utils.escape(column_name) for column_name in self.get_pk_names(
            do_sort=do_sort)]

    @property
    def name(self):
        return self._table_name

    def insert(self, engine, data, session):
        cmd = engine.dialect.insert(table=self, data=data)
        return cmd.execute(session=session)

    def update(self, engine, ids, data, session):
        cmd = engine.dialect.update(table=self, ids=ids, data=data)
        return cmd.execute(session=session)

    def delete(self, engine, ids, session):
        cmd = engine.dialect.delete(table=self, ids=ids)
        return cmd.execute(session=session)

    def select(self, engine, filters, session,
               limit=None, order_by=None, locked=False):
        """

        Warning: query with and w/o (limit or group_by) won't flush each other
        if cached!
        """
        cmd = engine.dialect.select(table=self, filters=filters, limit=limit,
                                    order_by=order_by, locked=locked)
        return cmd.execute(session=session)

    def custom_select(self, engine, where_conditions, where_values,
                      session, limit=None, order_by=None, locked=False):
        cmd = engine.dialect.custom_select(
            table=self,
            where_conditions=where_conditions,
            where_values=where_values,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        return cmd.execute(session=session)

    def count(self, engine, session, filters):
        cmd = engine.dialect.count(table=self, filters=filters)
        return cmd.execute(session=session)
