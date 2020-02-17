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

import contextlib
import logging
import threading


class SessionQueryCache(object):

    def __init__(self, session):
        super(SessionQueryCache, self).__init__()
        self._session = session
        self.__query_cache = {}

    @staticmethod
    def _get_hash(engine, table, filters, limit=None,
                  order_by=None, locked=False):
        query = engine.dialect.select(table, filters, limit, order_by, locked)
        values = query.get_values()
        statement = query.get_statement()
        return hash(tuple([statement] + values))

    @staticmethod
    def _get_hash_by_query(
            engine, table, where_conditions, where_values, limit=None,
            order_by=None, locked=False):
        query = engine.dialect.custom_select(
            table=table,
            where_conditions=where_conditions,
            where_values=where_values,
            limit=limit,
            order_by=order_by,
            locked=locked,
        )
        values = query.get_values()
        statement = query.get_statement()
        return hash(tuple([statement] + values))

    def get_all(self, engine, table, filters, fallback, limit=None,
                order_by=None, locked=False):
        query_hash = self._get_hash(engine, table, filters, limit, locked)
        if query_hash not in self.__query_cache:
            self.__query_cache[query_hash] = fallback(filters=filters,
                                                      session=self._session,
                                                      limit=limit,
                                                      order_by=order_by,
                                                      locked=locked)
        return self.__query_cache[query_hash]

    def query(self, engine, table, where_conditions, where_values, fallback,
              limit=None, order_by=None, locked=False):
        query_hash = self._get_hash_by_query(
            engine, table, where_conditions, where_values, limit, locked)
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


class MySQLSession(object):

    def __init__(self, conn):
        self._conn = conn
        self._cursor = conn.cursor(dictionary=True, buffered=True)
        self._log = logging.getLogger(__name__)
        self.cache = SessionQueryCache(session=self)

    def execute(self, statement, values):
        self._log.debug("Execute statement %s with values %s",
                        statement, values)
        self._cursor.execute(statement, values)
        return self._cursor

    def rollback(self):
        self._conn.rollback()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


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

    def __init__(self):
        super(SessionThreadStorage, self).__init__()
        self._storage = threading.local()

    def get_session(self):
        thread_session = getattr(self._storage, 'session', None)
        if thread_session is None:
            raise SessionNotFound('A session is not exists for this thread')
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
            raise SessionConflict("Another session %r is already stored!",
                                  thread_session)
        except SessionNotFound:
            self._storage.session = session
            return self._storage.session
