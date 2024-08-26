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
import contextlib
import logging

from mysql.connector import pooling
import six
from six.moves.urllib import parse

from restalchemy.common import singletons
from restalchemy.storage.sql.dialect import adapters
from restalchemy.storage.sql.dialect import mysql
from restalchemy.storage.sql import sessions


DEFAULT_NAME = 'default'
DEFAULT_CONNECTION_TIMEOUT = 10
LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractEngine(object):

    @abc.abstractproperty
    def URL_SCHEMA(self):
        raise NotImplementedError()

    def __init__(self, db_url):
        super(AbstractEngine, self).__init__()
        self._db_url = parse.urlparse(db_url)

    @abc.abstractproperty
    def db_name(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def db_username(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def db_password(self):
        raise NotImplementedError()


class MySQLEngine(AbstractEngine):

    URL_SCHEMA = 'mysql'

    def __init__(self, db_url, config=None, query_cache=False):
        super(MySQLEngine, self).__init__(db_url)
        if self._db_url.scheme != self.URL_SCHEMA:
            raise ValueError("Database url should be starts with mysql://. "
                             "For example: mysql://username:password@"
                             "127.0.0.1:3306/database_name")
        config = config or {}
        self._db_name = self._db_url.path[1:]
        if 'connection_timeout' not in config:
            config['connection_timeout'] = DEFAULT_CONNECTION_TIMEOUT
        config.update({
            'user': self.db_username,
            'password': self.db_password,
            'database': self.db_name,
            'host': self.db_host,
            'port': self.db_port,
            'converter_class': adapters.MySQLConverter
        })

        try:
            self._pool = pooling.MySQLConnectionPool(**config)
        except AttributeError as e:
            pool_name = e.args[0].split("'")[1]
            new_name = str(hash(pool_name))
            LOG.warning("Changing '%s' pool name to '%s'",
                        pool_name, new_name)
            config["pool_name"] = new_name
            self._pool = pooling.MySQLConnectionPool(**config)

        self._dialect = mysql.MySQLDialect()
        self._session_storage = sessions.SessionThreadStorage()
        self._query_cache = query_cache

    def __del__(self):
        pool = getattr(self, '_pool', None)
        if pool is not None:
            self._pool._remove_connections()

    @property
    def query_cache(self):
        return self._query_cache

    @property
    def dialect(self):
        return self._dialect

    @property
    def db_name(self):
        return self._db_name

    @property
    def db_username(self):
        return self._db_url.username

    @property
    def db_password(self):
        return self._db_url.password

    @property
    def db_host(self):
        return self._db_url.hostname

    @property
    def db_port(self):
        return self._db_url.port or 3306

    def get_connection(self):
        return self._pool.get_connection()

    def get_session(self):
        return sessions.MySQLSession(engine=self)

    def _get_session_from_storage(self):
        try:
            return self.get_session_storage().get_session()
        except sessions.SessionNotFound:
            return None

    @contextlib.contextmanager
    def session_manager(self, session=None):
        session = session or self._get_session_from_storage()
        if session is None:
            session = self.get_session()
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

    def get_session_storage(self):
        return self._session_storage


class EngineFactory(singletons.InheritSingleton):

    def __init__(self):
        super(EngineFactory, self).__init__()
        self._engines = {}
        self._engines_map = {
            MySQLEngine.URL_SCHEMA: MySQLEngine
        }

    def configure_factory(self, db_url, config=None, query_cache=False,
                          name=DEFAULT_NAME):
        """Configure_factory

        @property db_url: str. For example driver://user:passwd@host:port/db
        """
        schema = db_url.split(':')[0]
        try:
            self._engines[name] = self._engines_map[schema.lower()](
                db_url=db_url,
                config=config,
                query_cache=query_cache
            )
        except KeyError:
            raise ValueError("Can not find driver for schema %s" % schema)

    def get_engine(self, name=DEFAULT_NAME):
        engine = self._engines.get(name, None)
        if engine:
            return engine
        raise ValueError(("Can not return %s engine. Please configure"
                         " EngineFactory") % name)

    def destroy_engine(self, name=DEFAULT_NAME):
        try:
            del self._engines[name]
        except KeyError:
            pass

    def destroy_all_engines(self):
        self._engines = {}


class DBConnectionUrl(object):

    _CENSORED = ':<censored>@'

    def __init__(self, db_url):
        super(DBConnectionUrl, self).__init__()
        self._db_url = parse.urlparse(db_url)

    def __repr__(self):
        if self._db_url.password is None:
            orig_substr = "@"
        else:
            orig_substr = ":%s@" % self._db_url.password
        return self.url.replace(orig_substr, self._CENSORED)

    @property
    def url(self):
        return self._db_url.geturl()


engine_factory = EngineFactory()
