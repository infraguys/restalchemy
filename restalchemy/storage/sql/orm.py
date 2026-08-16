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

import orjson

from restalchemy.common import exceptions as common_exc
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import models
from restalchemy.dm import relationships as ra_relationships
from restalchemy.storage import base
from restalchemy.storage import exceptions
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import tables
from restalchemy.storage.sql.dialect import exceptions as exc


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
        return self.model_cls.restore_many_from_storage(
            result.rows,
            session=session,
        )

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
            raise exceptions.RecordNotFound(model=self.model_cls, filters=filters)
        else:
            raise exceptions.HasManyRecords(model=self.model_cls, filters=filters)

    def get_one_or_none(self, filters=None, session=None, cache=False, locked=False):
        try:
            return self.get_one(
                filters=filters, session=session, cache=cache, locked=locked
            )
        except exceptions.RecordNotFound:
            return None

    def _query(self, where_conditions, where_values, session, limit, order_by, locked):
        result = self._table.custom_select(
            engine=self._engine,
            where_conditions=where_conditions,
            where_values=where_values,
            session=session,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        return self.model_cls.restore_many_from_storage(
            result.fetchall(),
            session=session,
        )

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
            result = self._table.count(engine=self._engine, session=s, filters=filters)
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

    # Per class: the callable that turns a stored column into a model
    # value, per property name. Which one it is a declaration decides, and
    # it was looked up again -- a mapping lookup and two calls -- per
    # column per row read.
    OPERATIONAL_STORAGE_LOADERS_KEY = "storage_loaders"

    @classmethod
    def _get_storage_loaders(cls):
        try:
            return cls.__operational_storage__.get(
                cls.OPERATIONAL_STORAGE_LOADERS_KEY,
            )
        except common_exc.NotFoundOperationalStorageError:
            loaders = {
                name: prop.get_property_type().from_simple_type
                for name, prop in cls.properties.properties.items()
            }
            cls.__operational_storage__.store(
                cls.OPERATIONAL_STORAGE_LOADERS_KEY,
                loaders,
            )
            return loaders

    # Per class: the relationships a row carries as an identifier, and the
    # model each points at. A query that prefetched a relationship brings
    # the row of it along, and those are not among these.
    OPERATIONAL_STORAGE_DEFERRED_KEY = "deferred_relationships"

    # How many identifiers one query asks for. There is no reason to
    # split a hundred, and a reason not to hand a driver a hundred
    # thousand at once.
    RELATIONSHIP_BATCH_SIZE = 1000

    @classmethod
    def _get_deferred_relationships(cls):
        try:
            return cls.__operational_storage__.get(
                cls.OPERATIONAL_STORAGE_DEFERRED_KEY,
            )
        except common_exc.NotFoundOperationalStorageError:
            deferred = {}
            for name, prop in cls.properties.properties.items():
                prop_class = prop.get_property_class()
                if not (
                    isinstance(prop_class, type)
                    and issubclass(prop_class, ra_relationships.BaseRelationship)
                ):
                    continue
                if prop.is_prefetch():
                    continue
                target = prop.get_property_type()
                if isinstance(target, type) and issubclass(target, SQLStorableMixin):
                    deferred[name] = target
            cls.__operational_storage__.store(
                cls.OPERATIONAL_STORAGE_DEFERRED_KEY,
                deferred,
            )
            return deferred

    @classmethod
    def restore_many_from_storage(cls, rows, session=None):
        """Restore rows, asking for a relationship once, not once per row.

        A relationship the query did not prefetch reaches the model as an
        identifier, and turning it into the object it names is a query --
        per row, and per relationship. Sixty rows of a model with two
        relationships were a hundred and twenty round trips behind the one
        that read them.

        The identifiers of a whole page are asked for together instead,
        which is one query per relationship. What that does not find is
        left as it arrived, so a row pointing at something that is not
        there fails where it always did.
        """
        rows = list(rows)
        if len(rows) > 1:
            cls._preload_relationships(rows, session)
        return [cls.restore_row(row) for row in rows]

    @classmethod
    def _preload_relationships(cls, rows, session):
        for name, target in cls._get_deferred_relationships().items():
            try:
                id_name = target.get_id_property_name()
            except TypeError:
                # A model that does not answer with one identifier cannot
                # be asked for a page of them. The per-row path takes it,
                # as it always did.
                continue
            id_type = target.properties.properties[id_name].get_property_type()

            found = {}
            wanted = []
            for row in rows:
                value = row.get(name)
                if value is None or isinstance(value, (models.Model, dict)):
                    # Already an object, or a prefetched row of one.
                    continue
                try:
                    key = id_type.from_simple_type(value)
                except (ValueError, TypeError):
                    # Not an identifier this model can read. Leave it to
                    # the per-row path to fail the way it would have.
                    continue
                found.setdefault(key, None)
                wanted.append((row, key))

            if not wanted:
                continue

            keys = list(found)
            batch = cls.RELATIONSHIP_BATCH_SIZE
            for start in range(0, len(keys), batch):
                for obj in target.objects.get_all(
                    filters={id_name: dm_filters.In(keys[start : start + batch])},
                    session=session,
                ):
                    found[obj.get_id()] = obj

            for row, key in wanted:
                obj = found.get(key)
                if obj is not None:
                    row[name] = obj

    @classmethod
    def restore_from_storage(cls, **kwargs):
        return cls.restore_row(kwargs)

    @classmethod
    def restore_row(cls, row):
        """The model a stored row stands for.

        Takes the row as it is rather than spelled out as keywords: a
        page of rows is a page of mappings, and every `**` between here
        and the model builds another one.
        """
        obj = cls.restore_values(row, cls._get_storage_loaders())
        # Past `__setattr__`, which is there to tell a property name from
        # a plain attribute, and this one is known not to be one.
        object.__setattr__(obj, "_saved", True)
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
                        data=self._get_prepared_data(self.get_data_properties()),
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
                    raise exceptions.MultipleUpdatesDetected(model=self, filters={})

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
        if isinstance(value, cls):
            # Already the object it names: a collection resolves the
            # relationships of a whole page at once and leaves what it
            # found in the rows.
            return value
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
                kwargs[field] = orjson.loads(kwargs[field])
        return super(SQLStorableWithJSONFieldsMixin, cls).restore_from_storage(**kwargs)

    def _get_prepared_data(self, properties=None):
        if self.__jsonfields__ is None:
            raise UndefinedAttribute(attr_name="__jsonfields__")
        result = super(SQLStorableWithJSONFieldsMixin, self)._get_prepared_data(
            properties
        )
        if properties is None:
            json_properties = self.__jsonfields__
        else:
            json_properties = set(self.__jsonfields__).intersection(
                set(properties.keys())
            )
        for field in json_properties:
            result[field] = orjson.dumps(
                result[field], option=orjson.OPT_NON_STR_KEYS
            ).decode()
        return result
