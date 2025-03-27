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

from restalchemy.common import exceptions as common_exc
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.storage import base
from restalchemy.storage import exceptions
from restalchemy.storage.sql.dialect import exceptions as exc
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import tables


class ObjectCollection(
    base.AbstractObjectCollection, base.AbstractObjectCollectionCountMixin
):

    @property
    def _table(self):
        return self.model_cls.get_table()

    @property
    def _engine(self):
        return engines.engine_factory.get_engine()

    @base.error_catcher
    def get_all(
        self,
        filters=None,
        session=None,
        cache=False,
        limit=None,
        order_by=None,
        locked=False,
    ):
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

            return self._get_all(
                filters=filters,
                session=s,
                limit=limit,
                order_by=order_by,
                locked=locked,
            )

    def _get_all(self, filters, session, limit, order_by=None, locked=False):
        result = self._table.select(
            engine=self._engine,
            filters=filters,
            limit=limit,
            order_by=order_by,
            session=session,
            locked=locked,
        )
        return [
            self.model_cls.restore_from_storage(**params)
            for params in result.rows
        ]

    @base.error_catcher
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
            raise exceptions.RecordNotFound(
                model=self.model_cls, filters=filters
            )
        else:
            raise exceptions.HasManyRecords(
                model=self.model_cls, filters=filters
            )

    def get_one_or_none(
        self, filters=None, session=None, cache=False, locked=False
    ):
        try:
            return self.get_one(
                filters=filters, session=session, cache=cache, locked=locked
            )
        except exceptions.RecordNotFound:
            return None

    def _query(
        self, where_conditions, where_values, session, limit, order_by, locked
    ):
        result = self._table.custom_select(
            engine=self._engine,
            where_conditions=where_conditions,
            where_values=where_values,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        return [
            self.model_cls.restore_from_storage(**params)
            for params in list(result.fetchall())
        ]

    @base.error_catcher
    def query(
        self,
        where_conditions,
        where_values,
        session=None,
        cache=False,
        limit=None,
        order_by=None,
        locked=False,
    ):
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

            return self._query(
                where_conditions=where_conditions,
                where_values=where_values,
                session=s,
                limit=limit,
                order_by=order_by,
                locked=locked,
            )

    @base.error_catcher
    def count(self, session=None, filters=None):
        with self._engine.session_manager(session=session) as s:
            result = self._table.count(
                engine=self._engine, session=s, filters=filters
            )
            data = list(result.fetchall())
            return data[0]["count"]


class UndefinedAttribute(common_exc.RestAlchemyException):

    message = "Class attribute %(attr_name)s must be provided."


class SQLStorableMixin(base.AbstractStorableMixin, metaclass=abc.ABCMeta):

    _saved = False

    _ObjectCollection = ObjectCollection

    __tablename__ = None

    @classmethod
    def get_table(cls):
        try:
            table = cls.__operational_storage__.get(
                tables.OPERATIONAL_STORAGE_SIMPLE_TABLE_KEY,
            )
        except common_exc.NotFoundOperationalStorageError:
            if cls.__tablename__ is None:
                raise UndefinedAttribute(attr_name="__tablename__")
            table = tables.SQLTable(
                engine=cls._get_engine(),
                table_name=cls.__tablename__,
                model=cls,
            )
            cls.__operational_storage__.store(
                tables.OPERATIONAL_STORAGE_SIMPLE_TABLE_KEY,
                table,
            )
        return table

    @classmethod
    def _get_engine(cls):
        return engines.engine_factory.get_engine()

    @classmethod
    def restore_from_storage(cls, **kwargs):
        model_format = {}
        for name, value in kwargs.items():
            model_format[name] = (
                cls.properties.properties[name]
                .get_property_type()
                .from_simple_type(value)
            )
        obj = cls.restore(**model_format)
        obj._saved = True
        return obj

    @base.error_catcher
    @base.dead_lock_catcher
    def insert(self, session=None):
        # TODO(efrolov): Add filters parameters.
        with self._get_engine().session_manager(session=session) as s:
            try:
                self.get_table().insert(
                    engine=self._get_engine(),
                    data=self._get_prepared_data(),
                    session=s,
                )
                # TODO(efrolov): Check result
            except exc.Conflict as e:
                raise exceptions.ConflictRecords(model=self, msg=str(e))
            self._saved = True

    def save(self, session=None):
        # TODO(efrolov): Add filters parameters.
        self.update(session) if self._saved else self.insert(session)

    @base.error_catcher
    @base.dead_lock_catcher
    def update(self, session=None, force=False):
        # TODO(efrolov): Add filters parameters.
        if self.is_dirty() or force:
            self.validate()
            with self._get_engine().session_manager(session=session) as s:
                try:
                    result = self.get_table().update(
                        engine=self._get_engine(),
                        ids=self._get_prepared_data(self.get_id_properties()),
                        data=self._get_prepared_data(
                            self.get_data_properties()
                        ),
                        session=s,
                    )
                except exc.Conflict as e:
                    raise exceptions.ConflictRecords(model=self, msg=str(e))
                if result.get_count() == 0:
                    _filters = {
                        name: dm_filters.EQ(prop.value)
                        for name, prop in self.get_id_properties().items()
                    }
                    type(self).objects.get_one(filters=_filters, session=s)
                if result.get_count() > 1:
                    raise exceptions.MultipleUpdatesDetected(
                        model=self, filters={}
                    )

    @base.error_catcher
    @base.dead_lock_catcher
    def delete(self, session=None):
        # TODO(efrolov): Add filters parameters.
        with self._get_engine().session_manager(session=session) as s:
            result = self.get_table().delete(
                engine=self._get_engine(),
                ids=self._get_prepared_data(self.get_id_properties()),
                session=s,
            )
            # TODO(efrolov): Check result
            return result

    @classmethod
    def to_simple_type(cls, value):
        if value is None:
            return None
        id_type = cls.get_id_property().popitem()[-1].get_property_type()
        if isinstance(value, models.Model):
            return id_type.to_simple_type(value.get_id())
        # Allow to filter by id without full model
        return id_type.to_simple_type(value)

    @classmethod
    @base.dead_lock_catcher
    def from_simple_type(cls, value):
        if value is None:
            return None
        if isinstance(value, base.PrefetchResult):
            for name in cls.id_properties.keys():
                if value[name]:
                    break
            else:
                return None
            return cls.restore_from_storage(**value)
        for name in cls.id_properties:
            value = (
                cls.properties.properties[name]
                .get_property_type()
                .from_simple_type(value)
            )
            engine = engines.engine_factory.get_engine()
            return cls.objects.get_one(
                filters={name: dm_filters.EQ(value)}, cache=engine.query_cache
            )


class SQLStorableWithJSONFieldsMixin(SQLStorableMixin, metaclass=abc.ABCMeta):
    """Use only if database's client doesn't support JSON fields natively."""

    __jsonfields__ = None

    @classmethod
    def restore_from_storage(cls, **kwargs):
        if cls.__jsonfields__ is None:
            raise UndefinedAttribute(attr_name="__jsonfields__")
        kwargs = kwargs.copy()
        for field in cls.__jsonfields__:
            # Some databases' clients support JSON fields natively.
            if isinstance(kwargs[field], str):
                kwargs[field] = json.loads(kwargs[field])
        return super(SQLStorableWithJSONFieldsMixin, cls).restore_from_storage(
            **kwargs
        )

    def _get_prepared_data(self, properties=None):
        if self.__jsonfields__ is None:
            raise UndefinedAttribute(attr_name="__jsonfields__")
        result = super(
            SQLStorableWithJSONFieldsMixin, self
        )._get_prepared_data(properties)
        if properties is None:
            json_properties = self.__jsonfields__
        else:
            json_properties = set(self.__jsonfields__).intersection(
                set(properties.keys())
            )
        for field in json_properties:
            result[field] = json.dumps(result[field], separators=(",", ":"))
        return result
