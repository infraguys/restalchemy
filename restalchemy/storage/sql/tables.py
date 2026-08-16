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


import weakref

OPERATIONAL_STORAGE_SIMPLE_TABLE_KEY = "table"


class SQLTable(object):
    """The columns of a model, as a statement names them.

    Which columns there are, in which order, and how the engine escapes
    them, a model's declaration and the engine settle between them. Every
    statement built asked again -- a walk over the properties and a sort,
    then an escape per column -- so the answers are kept: by shape for the
    names, by engine for the escaped ones, since a model can be read
    through one engine and written through another.
    """

    def __init__(self, engine, table_name, model):
        super(SQLTable, self).__init__()
        self._table_name = table_name
        self._model = model
        self._column_names = {}
        # Weak on the engine: a table is kept for the life of the model
        # it belongs to, and holding an engine here would outlive the
        # engine's own life -- and with it, its open connections.
        self._escaped_names = weakref.WeakKeyDictionary()

    @property
    def model(self):
        return self._model

    def get_column_names(self, session, with_pk=True, do_sort=True):
        key = (with_pk, do_sort)
        result = self._column_names.get(key)
        if result is None:
            result = []
            for name, prop in self._model.properties.items():
                if not with_pk and prop.is_id_property():
                    continue
                result.append(name)
            if do_sort:
                result.sort()
            self._column_names[key] = result
        return result

    def get_escaped_column_names(self, session, with_pk=True, do_sort=True):
        by_shape = self._escaped_for(session.engine)
        key = ("columns", with_pk, do_sort)
        result = by_shape.get(key)
        if result is None:
            result = [
                session.engine.escape(column_name)
                for column_name in self.get_column_names(
                    session=session,
                    with_pk=with_pk,
                    do_sort=do_sort,
                )
            ]
            by_shape[key] = result
        return result

    def _escaped_for(self, engine):
        by_shape = self._escaped_names.get(engine)
        if by_shape is None:
            by_shape = {}
            self._escaped_names[engine] = by_shape
        return by_shape

    def get_pk_names(self, session, do_sort=True):
        key = ("pk", do_sort)
        result = self._column_names.get(key)
        if result is None:
            result = []
            for name, prop in self._model.properties.items():
                if prop.is_id_property():
                    result.append(name)
            if do_sort:
                result.sort()
            self._column_names[key] = result
        return result

    def get_escaped_pk_names(self, session, do_sort=True):
        by_shape = self._escaped_for(session.engine)
        key = ("pk", do_sort)
        result = by_shape.get(key)
        if result is None:
            result = [
                session.engine.escape(column_name)
                for column_name in self.get_pk_names(
                    session=session,
                    do_sort=do_sort,
                )
            ]
            by_shape[key] = result
        return result

    @property
    def name(self):
        return self._table_name

    def insert(self, engine, data, session):
        cmd = engine.dialect.insert(
            table=self,
            data=data,
            session=session,
        )
        return cmd.execute()

    def update(self, engine, ids, data, session):
        cmd = engine.dialect.update(
            table=self,
            ids=ids,
            data=data,
            session=session,
        )
        return cmd.execute()

    def delete(self, engine, ids, session):
        cmd = engine.dialect.delete(
            table=self,
            ids=ids,
            session=session,
        )
        return cmd.execute()

    def select(self, engine, filters, session, limit=None, order_by=None, locked=False):
        """

        Warning: query with and w/o (limit or group_by) won't flush each other
        if cached!
        """
        q = engine.dialect.orm.select(self._model, session).where(
            filters=filters,
        )

        for name, sort_type in (order_by or {}).items():
            q.order_by(property_name=name, sort_type=sort_type)

        if limit:
            q.limit(limit)

        if locked:
            q.for_(share=not locked)

        cmd = engine.dialect.orm_command(
            table=self,
            query=q,
            session=session,
        )
        return cmd.execute()

    def custom_select(
        self,
        engine,
        where_conditions,
        where_values,
        session,
        limit=None,
        order_by=None,
        locked=False,
    ):
        cmd = engine.dialect.custom_select(
            table=self,
            where_conditions=where_conditions,
            where_values=where_values,
            limit=limit,
            order_by=order_by,
            locked=locked,
            session=session,
        )
        return cmd.execute()

    def count(self, engine, session, filters):
        cmd = engine.dialect.count(
            table=self,
            filters=filters,
            session=session,
        )
        return cmd.execute()
