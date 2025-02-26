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

import contextlib
import logging
import threading

from mysql.connector import errors
from psycopg import rows as pg_rows
from psycopg import errors as pg_errors

from restalchemy.storage import exceptions as exc
from restalchemy.storage.sql.dialect import mysql
from restalchemy.storage.sql.dialect import pgsql


LOG = logging.getLogger(__name__)


class SessionQueryCache(object):

    def __init__(self, session):
        super(SessionQueryCache, self).__init__()
        self._session = session
        self.__query_cache = {}

    def _get_hash(
        self, engine, table, filters, limit=None, order_by=None, locked=False
    ):
        query = engine.dialect.select(
            table=table,
            filters=filters,
            limit=limit,
            order_by=order_by,
            session=self._session,
            locked=locked,
        )
        values = query.get_values()
        statement = query.get_statement()
        return hash(tuple([statement] + values))

    def _get_hash_by_query(
        self,
        engine,
        table,
        where_conditions,
        where_values,
        limit=None,
        order_by=None,
        locked=False,
    ):
        query = engine.dialect.custom_select(
            table=table,
            where_conditions=where_conditions,
            where_values=where_values,
            limit=limit,
            order_by=order_by,
            session=self._session,
            locked=locked,
        )
        values = query.get_values()
        statement = query.get_statement()
        return hash(tuple([statement] + values))

    def get_all(
        self,
        engine,
        table,
        filters,
        fallback,
        limit=None,
        order_by=None,
        locked=False,
    ):
        query_hash = self._get_hash(engine, table, filters, limit, locked)
        if query_hash not in self.__query_cache:
            self.__query_cache[query_hash] = fallback(
                filters=filters,
                session=self._session,
                limit=limit,
                order_by=order_by,
                locked=locked,
            )
        return self.__query_cache[query_hash]

    def query(
        self,
        engine,
        table,
        where_conditions,
        where_values,
        fallback,
        limit=None,
        order_by=None,
        locked=False,
    ):
        query_hash = self._get_hash_by_query(
            engine, table, where_conditions, where_values, limit, locked
        )
        if query_hash not in self.__query_cache:
            self.__query_cache[query_hash] = fallback(
                where_conditions=where_conditions,
                where_values=where_values,
                session=self._session,
                limit=limit,
                order_by=order_by,
                locked=locked,
            )
        return self.__query_cache[query_hash]


class PgSQLSession(object):

    def __init__(self, engine):
        self._engine = engine
        self._conn = self._engine.get_connection()
        self._cursor = self._conn.cursor(row_factory=pg_rows.dict_row)
        self._log = LOG
        self.cache = SessionQueryCache(session=self)

    @property
    def engine(self):
        return self._engine

    @staticmethod
    def _check_models_same_type(target_model, models):
        model_type = type(target_model)
        if not min(map(lambda m: isinstance(m, model_type), models)):
            raise TypeError("All models in the list must be of the same type")

    def batch_insert(self, models):
        if models:
            # Check models type
            first_model = models[0]
            self._check_models_same_type(first_model, models)

            # process values
            values = []
            table = first_model.get_table()
            statement = pgsql.PgSQLInsert(
                table=table,
                data=first_model.get_storable_snapshot(),
                session=self,
            ).get_statement()
            for model in models:
                snapshot = model.get_storable_snapshot()
                insert = pgsql.PgSQLInsert(
                    table=table,
                    data=snapshot,
                    session=self,
                )
                values.append(insert.get_values())

            try:
                return self.execute_many(statement, values)
            except pg_errors.UniqueViolation as e:
                raise exc.ConflictRecords(
                    model=type(first_model).__name__,
                    msg=str(e),
                )

    def batch_delete(self, models):
        if models:
            # Check models type
            first_model = models[0]
            self._check_models_same_type(first_model, models)

            # process values
            table = first_model.get_table()
            values = []
            for model in models:
                pk_values = {}
                for name, prop in model.get_id_properties().items():
                    pk_values[name] = prop.property_type.to_simple_type(
                        prop.value
                    )
                values.append(pk_values)
            operation = pgsql.PgSQLBatchDelete(
                table=table,
                snapshot=values,
                session=self,
            )

            return self.execute(
                operation.get_statement(), operation.get_values()
            )

    def execute(self, statement, values=None):
        try:
            self._log.debug(
                (
                    "Execute statement %s"
                    " with values %s"
                    " within %s database"
                ),
                statement,
                values,
                self._engine.db_name,
            )
            self._cursor.execute(statement, values)
            return self._cursor
        except errors.DatabaseError:
            raise

    def execute_many(self, statement, values):
        self._log.debug(
            (
                "Execute batch statement %s"
                " with values %s"
                " within %s database"
            ),
            statement,
            values,
            self._engine.db_name,
        )
        self._cursor.executemany(statement, values)
        return self._cursor

    def rollback(self):
        self._conn.rollback()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._engine.close_connection(self._conn)


class MySQLSession(object):

    def __init__(self, engine):
        self._engine = engine
        self._conn = self._engine.get_connection()
        self._cursor = self._conn.cursor(dictionary=True, buffered=True)
        self._log = LOG
        self.cache = SessionQueryCache(session=self)

    @property
    def engine(self):
        return self._engine

    @staticmethod
    def _check_models_same_type(target_model, models):
        model_type = type(target_model)
        if not min(map(lambda m: isinstance(m, model_type), models)):
            raise TypeError("All models in the list must be of the same type")

    def batch_insert(self, models):
        if models:
            # Check models type
            first_model = models[0]
            self._check_models_same_type(first_model, models)

            # process values
            values = []
            table = first_model.get_table()
            statement = mysql.MySQLInsert(
                table=table,
                data=first_model.get_storable_snapshot(),
                session=self,
            ).get_statement()
            for model in models:
                snapshot = model.get_storable_snapshot()
                insert = mysql.MySQLInsert(
                    table=table,
                    data=snapshot,
                    session=self,
                )
                values.append(insert.get_values())

            try:
                return self.execute_many(statement, values)
            except errors.IntegrityError as e:
                # Error codes from Maria DB documentation. See more on website
                # https://mariadb.com/kb/en/mariadb-error-codes/
                # Errno: 1062 and sqlstate: 23000 is "Duplicate entry" error.
                if e.errno == 1062 and e.sqlstate == "23000":
                    raise exc.ConflictRecords(
                        model=type(first_model).__name__,
                        msg=e.msg,
                    )
                else:
                    raise exc.UnknownStorageException(caused=e)

    def batch_delete(self, models):
        if models:
            # Check models type
            first_model = models[0]
            self._check_models_same_type(first_model, models)

            # process values
            table = first_model.get_table()
            values = []
            for model in models:
                pk_values = {}
                for name, prop in model.get_id_properties().items():
                    pk_values[name] = prop.property_type.to_simple_type(
                        prop.value
                    )
                values.append(pk_values)
            operation = mysql.MySQLBatchDelete(
                table=table,
                snapshot=values,
                session=self,
            )

            return self.execute(
                operation.get_statement(), operation.get_values()
            )

    def execute(self, statement, values=None):
        try:
            self._log.debug(
                (
                    "Execute statement %s"
                    " with values %s"
                    " within %s database"
                ),
                statement,
                values,
                self._engine.db_name,
            )
            self._cursor.execute(statement, values)
            return self._cursor
        except errors.DatabaseError as e:
            if e.errno == 1213:
                raise exc.DeadLock(msg=e.msg)
            raise

    def execute_many(self, statement, values):
        self._log.debug(
            (
                "Execute batch statement %s"
                " with values %s"
                " within %s database"
            ),
            statement,
            values,
            self._engine.db_name,
        )
        self._cursor.executemany(statement, values)
        return self._cursor

    def rollback(self):
        self._conn.rollback()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._engine.close_connection(self._conn)


@contextlib.contextmanager
def session_manager(engine, session=None):
    if session is None:
        session = engine.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    else:
        yield session


class SessionConflict(Exception):
    pass


class SessionNotFound(Exception):
    pass


class SessionThreadStorage(object):

    _storage = threading.local()

    def __init__(self):
        super(SessionThreadStorage, self).__init__()

    def get_session(self):
        thread_session = getattr(self._storage, "session", None)
        if thread_session is None:
            raise SessionNotFound("A session is not exists for this thread")
        return thread_session

    def pop_session(self):
        try:
            return self.get_session()
        finally:
            self.remove_session()

    def remove_session(self):
        self._storage.session = None

    def store_session(self, session):
        try:
            thread_session = self.get_session()
            raise SessionConflict(
                "Another session %r is already stored!", thread_session
            )
        except SessionNotFound:
            self._storage.session = session
            return self._storage.session
