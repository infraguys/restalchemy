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

import six

from restalchemy.storage import base
from restalchemy.storage import exceptions
from restalchemy.storage.sql.dialect import exceptions as exc
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import filters as flt
from restalchemy.storage.sql import sessions
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

    def select(self, engine, filters, session):
        cmd = engine.dialect.select(table=self, filters=filters)
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
        # TODO(efrolov): Move this code from class to utils or another
        #                location.
        result = {}
        for name, value in filters.items():
            result[name] = (value if isinstance(value, flt.AbstractExpression)
                            else (self.model_cls.properties.properties[name]
                                  .get_property_type().to_simple_type(value)))
        return result

    def get_all(self, filters=None, session=None):
        # TODO(efrolov): Add limit and offset parameters
        filters = self._filters_to_storage_view(filters or {})
        with sessions.session_manager(self._engine, session)as s:
            result = self._table.select(engine=self._engine, filters=filters,
                                        session=s)
            for params in result.fetchall():
                yield self.model_cls.restore_from_storage(**params)

    def get_one(self, filters=None, session=None):
        result = list(self.get_all(filters=filters, session=session))
        result_len = len(result)
        if result_len == 1:
            return result[0]
        elif result_len == 0:
            raise exceptions.RecordNotFound(model=self.model_cls,
                                            filters=filters)
        else:
            raise exceptions.HasManyRecords(model=self.model_cls,
                                            filters=filters)


@six.add_metaclass(abc.ABCMeta)
class SQLStorableMixin(base.AbstractStorableMixin):

    _saved = False

    _ObjectCollection = ObjectCollection

    @abc.abstractproperty
    def __tablename__(self):
        raise NotImplementedError()

    @property
    def _table(self):
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
        obj = cls(**model_format)
        obj._saved = True
        return obj

    def insert(self, session=None):
        # TODO(efrolov): Add filters arameters.
        with sessions.session_manager(self._engine, session) as s:
            try:
                self._table.insert(engine=self._engine,
                                   data=self._get_prepared_data(),
                                   session=s)
                # TODO(efrolov): Check result
            except exc.Conflict as e:
                raise exceptions.ConflictRecords(model=self, msg=e.message)
            self._saved = True

    def save(self, session=None):
        # TODO(efrolov): Add filters arameters.
        self.update(session) if self._saved else self.insert(session)

    def update(self, session=None):
        # TODO(efrolov): Add filters arameters.
        with sessions.session_manager(self._engine, session) as s:
            try:
                result = self._table.update(
                    engine=self._engine,
                    ids=self._get_prepared_data(self.get_id_properties()),
                    data=self._get_prepared_data(self.get_data_properties()),
                    session=s)
            except exc.Conflict as e:
                raise exceptions.ConflictRecords(model=self, msg=e.message)
            if result.get_count() == 0:
                raise exceptions.RecordNotFound(model=self, filters=None)
            if result.get_count() > 1:
                raise exceptions.MultipleUpdatesDetected(model=self,
                                                         filters={})

    def delete(self, session=None):
        # TODO(efrolov): Add filters arameters.
        with sessions.session_manager(self._engine, session) as s:
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
                return cls.objects.get_one(filters={name: value})
