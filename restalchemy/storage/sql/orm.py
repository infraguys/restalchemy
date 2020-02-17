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

import abc
import json

import six

from restalchemy.common import exceptions as common_exc
from restalchemy.storage import base
from restalchemy.storage import exceptions
from restalchemy.storage.sql.dialect import exceptions as exc
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import filters as flt
from restalchemy.storage.sql import utils


class SQLTable(object):

    def __init__(self, table_name, model):
        super(SQLTable, self).__init__()
        self._table_name = table_name
        self._model = model

    def get_column_names(self, with_pk=True, do_sort=True):
        result = []
        for name, prop in self._model.properties.items():
            if with_pk == False and prop.is_id_property():
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
        '''

        Warning: query with and w/o (limit or group_by) won't flush each other
        if cached!
        '''
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


class ObjectCollection(base.AbstractObjectCollection):

    @property
    def _table(self):
        return SQLTable(table_name=self.model_cls.__tablename__,
                        model=self.model_cls)

    @property
    def _engine(self):
        return engines.engine_factory.get_engine()

    def _filters_to_storage_view(self, filters):
        result = {}
        for name, value in filters.items():
            value_type = (self.model_cls.properties.properties[name]
                          .get_property_type())
            result[name] = flt.convert_filter(value, value_type)
        return result

    def get_all(self, filters=None, session=None, cache=False, limit=None,
                order_by=None, locked=False):
        # TODO(efrolov): Add limit and offset parameters
        filters = self._filters_to_storage_view(filters or {})
        with self._engine.session_manager(session=session) as s:
            if cache is True:
                return s.cache.get_all(
                    engine=self._engine,
                    table=self._table,
                    filters=filters,
                    fallback=self._get_all,
                    limit=limit,
                    order_by=order_by,
                    locked=locked,
                )

            return self._get_all(filters=filters, session=s, limit=limit,
                                 order_by=order_by, locked=locked)

    def _get_all(self, filters, session, limit, order_by=None, locked=False):
        result = self._table.select(
            engine=self._engine, filters=filters, limit=limit,
            order_by=order_by, session=session, locked=locked)
        return [self.model_cls.restore_from_storage(**params)
                for params in list(result.fetchall())]

    def get_one(self, filters=None, session=None, cache=False, locked=False):
        result = self.get_all(
            filters=filters,
            session=session,
            cache=cache,
            limit=2,
            locked=locked,
        )
        result_len = len(result)
        if result_len == 1:
            return result[0]
        elif result_len == 0:
            raise exceptions.RecordNotFound(model=self.model_cls,
                                            filters=filters)
        else:
            raise exceptions.HasManyRecords(model=self.model_cls,
                                            filters=filters)

    def _query(self, where_conditions, where_values,
               session, limit, order_by, locked):
        result = self._table.custom_select(
            engine=self._engine,
            where_conditions=where_conditions,
            where_values=where_values,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        return [self.model_cls.restore_from_storage(**params)
                for params in list(result.fetchall())]

    def query(self, where_conditions, where_values, session=None,
              cache=False, limit=None, order_by=None, locked=False):
        """

        :param where_conditions: "NOT (bala < %s)"
        :param where_values: (5, 10,)
        """
        with self._engine.session_manager(session=session) as s:
            if cache is True:
                return s.cache.query(
                    engine=self._engine,
                    table=self._table,
                    where_conditions=where_conditions,
                    where_values=where_values,
                    fallback=self._query,
                    limit=limit,
                    order_by=order_by,
                    locked=locked,
                )

            return self._query(where_conditions=where_conditions,
                               where_values=where_values,
                               session=s,
                               limit=limit,
                               order_by=order_by,
                               locked=locked)


class UndefinedAttribute(common_exc.RestAlchemyException):

    message = "Class attribute %(attr_name)s must be provided."


@six.add_metaclass(abc.ABCMeta)
class SQLStorableMixin(base.AbstractStorableMixin):

    _saved = False

    _ObjectCollection = ObjectCollection

    __tablename__ = None

    @property
    def _table(self):
        if self.__tablename__ is None:
            raise UndefinedAttribute(attr_name='__tablename__')
        return SQLTable(table_name=self.__tablename__, model=self)

    @property
    def _engine(self):
        return engines.engine_factory.get_engine()

    @classmethod
    def restore_from_storage(cls, **kwargs):
        model_format = {}
        for name, value in kwargs.items():
            model_format[name] = (cls.properties.properties[name]
                                  .get_property_type()
                                  .from_simple_type(value))
        obj = cls.restore(**model_format)
        obj._saved = True
        return obj

    def insert(self, session=None):
        # TODO(efrolov): Add filters parameters.
        with self._engine.session_manager(session=session) as s:
            try:
                self._table.insert(engine=self._engine,
                                   data=self._get_prepared_data(),
                                   session=s)
                # TODO(efrolov): Check result
            except exc.Conflict as e:
                raise exceptions.ConflictRecords(model=self, msg=e.message)
            self._saved = True

    def save(self, session=None):
        # TODO(efrolov): Add filters parameters.
        self.update(session) if self._saved else self.insert(session)

    def update(self, session=None, force=False):
        # TODO(efrolov): Add filters parameters.
        if self.is_dirty() or force:
            with self._engine.session_manager(session=session) as s:
                try:
                    result = self._table.update(
                        engine=self._engine,
                        ids=self._get_prepared_data(self.get_id_properties()),
                        data=self._get_prepared_data(
                            self.get_data_properties()),
                        session=s)
                except exc.Conflict as e:
                    raise exceptions.ConflictRecords(model=self, msg=e.message)
                if result.get_count() == 0:
                    filters = {name: prop.value for name, prop in
                               self.get_id_properties().items()}
                    type(self).objects.get_one(filters=filters)
                if result.get_count() > 1:
                    raise exceptions.MultipleUpdatesDetected(model=self,
                                                             filters={})

    def delete(self, session=None):
        # TODO(efrolov): Add filters parameters.
        with self._engine.session_manager(session=session) as s:
            result = self._table.delete(
                engine=self._engine,
                ids=self._get_prepared_data(self.get_id_properties()),
                session=s)
            # TODO(efrolov): Check result
            return result

    @classmethod
    def to_simple_type(cls, value):
        if value is None:
            return None
        for prop in value.properties.values():
            if prop.is_id_property():
                return prop.property_type.to_simple_type(value.get_id())
        raise ValueError("Model (%s) should contain a property of IdProperty "
                         "type" % value)

    @classmethod
    def from_simple_type(cls, value):
        if value is None:
            return None
        for name, prop in cls.properties.items():
            if prop.is_id_property():
                value = (cls.properties.properties[name].get_property_type()
                         .from_simple_type(value))
                engine = engines.engine_factory.get_engine()
                return cls.objects.get_one(filters={name: value},
                                           cache=engine.query_cache)


@six.add_metaclass(abc.ABCMeta)
class SQLStorableWithJSONFieldsMixin(SQLStorableMixin):

    __jsonfields__ = None

    @classmethod
    def restore_from_storage(cls, **kwargs):
        if cls.__jsonfields__ is None:
            raise UndefinedAttribute(attr_name='__jsonfields__')
        kwargs = kwargs.copy()
        for field in cls.__jsonfields__:
            kwargs[field] = json.loads(kwargs[field])
        return super(SQLStorableWithJSONFieldsMixin, cls
                     ).restore_from_storage(**kwargs)

    def _get_prepared_data(self, properties=None):
        if self.__jsonfields__ is None:
            raise UndefinedAttribute(attr_name='__jsonfields__')
        result = super(SQLStorableWithJSONFieldsMixin, self
                       )._get_prepared_data(properties)
        if properties is None:
            json_properties = self.__jsonfields__
        else:
            json_properties = set(self.__jsonfields__).intersection(
                set(properties.keys()))
        for field in json_properties:
            result[field] = json.dumps(result[field])
        return result
