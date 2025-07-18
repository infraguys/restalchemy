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
import urllib.parse as parse

from mysql.connector import pooling
import psycopg_pool
from psycopg.types.json import Jsonb, JsonbDumper

from restalchemy.common import constants as c
from restalchemy.common import singletons
from restalchemy.storage.sql.dialect import adapters
from restalchemy.storage.sql.dialect import mysql
from restalchemy.storage.sql.dialect import pgsql
from restalchemy.storage.sql import sessions


DEFAULT_NAME = "default"
DEFAULT_CONNECTION_TIMEOUT = 10
LOG = logging.getLogger(__name__)


class AbstractEngine(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def URL_SCHEMA(self):
        """
        The URL schema for the database engine.

        This abstract property should be overridden by subclasses to specify
        the schema used in the database connection URL (e.g., "postgresql").
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def DEFAULT_PORT(self):
        """The default port number used by the database engine.

        This abstract property should be overridden by subclasses to specify
        the default port number used by the database engine if it is not
        specified in the database connection URL.
        """
        raise NotImplementedError()

    def __init__(
        self,
        db_url,
        dialect,
        session_storage,
        config=None,
        query_cache=False,
    ):
        """
        Initializes the database engine.

        :param db_url: The URL of the database connection.
        :param dialect: The SQL dialect used by the database engine.
        :param session_storage: The type of session storage used by the engine.
        :param config: A dictionary of configuration options for the engine.
        :param query_cache: A boolean indicating whether the engine should
                            cache query results.

        :raises ValueError: If the database URL does not match the expected
            format.
        """
        super(AbstractEngine, self).__init__()
        self._db_url = parse.urlparse(db_url)

        if self._db_url.scheme != self.URL_SCHEMA:
            raise ValueError(
                "Database url should be starts with "
                f"{self.URL_SCHEMA}://. For example: "
                "mysql://<username>:[password]@"
                "<host>:[port]/<database_name>"
            )

        self._db_name = self._db_url.path[1:]
        self._config = config or {}
        self._dialect = dialect
        self._session_storage = session_storage
        self._query_cache = query_cache

    @property
    def dialect(self):
        """
        Returns the SQL dialect used by the database engine.

        :return: The SQL dialect used by the database engine.
        :rtype: AbstractDialect
        """
        return self._dialect

    def escape(self, value):
        """
        Escapes a value for use in a query.

        Escapes a value by wrapping it in backticks. This is a common way to
        escape values in SQL queries.

        :param value: The value to be escaped.
        :return: The escaped value.
        :rtype: str
        """
        return "`%s`" % value

    @property
    def db_name(self):
        """
        Returns the name of the database.

        This property retrieves the database name from the parsed URL of the
        database connection, which is stored during the initialization of the
        engine instance.
        """

        return self._db_name

    @property
    def db_username(self):
        """
        Returns the username used for the database connection.

        This property retrieves the username from the parsed URL of the
        database connection, which is stored during the initialization of the
        engine instance.
        """
        return self._db_url.username

    @property
    def db_password(self):
        """
        Returns the password used for the database connection.

        This property retrieves the password from the parsed URL of the
        database connection, which is stored during the initialization of the
        engine instance.
        """
        return self._db_url.password

    @property
    def db_host(self):
        """
        Returns the hostname used for the database connection.

        This property retrieves the hostname from the parsed URL of the
        database connection, which is stored during the initialization of the
        engine instance.
        """
        return self._db_url.hostname

    @property
    def db_port(self):
        """
        Returns the port number used for the database connection.

        If the port number was not specified in the database connection URL,
        the default port number for the engine is used instead.

        Returns:
            The port number used for the database connection.
        """
        return self._db_url.port or self.DEFAULT_PORT

    @property
    def query_cache(self):
        """
        Returns a boolean indicating whether the query cache is enabled.

        The query cache can be set when the engine is initialized, and it
        determines whether the engine should cache the results of queries
        using the session's query cache.

        Returns:
            A boolean indicating whether the query cache is enabled.
        """
        return self._query_cache

    def get_connection(self):
        """
        Establishes and returns a connection to the database from a pool.

        This method should be implemented by subclasses to provide the logic
        for connecting to a specific database using the engine's
        configuration.

        Returns:
            A database connection object.

        Raises:
            NotImplementedError: If the method is not implemented by a
            subclass.
        """
        raise NotImplementedError()

    def get_session(self):
        """
        Returns a session object for the engine. This method can be used to
        explicitly start a session, or to get the session object from the
        current context.

        Returns:
            A session object.

        Raises:
            NotImplementedError: If the method is not implemented by a
            subclass.
        """
        raise NotImplementedError()

    def _get_session_from_storage(self):
        """
        Retrieve a session object from the session storage associated with
        this engine.

        :returns: A session object, or None if no session is stored.
        :rtype: Session or None
        """
        try:
            return self.get_session_storage().get_session()
        except sessions.SessionNotFound:
            return None

    @contextlib.contextmanager
    def session_manager(self, session=None):
        """
        Context manager for managing a database session.

        This method provides a context for executing database operations within
        a session. If a session is not provided, it attempts to retrieve one
        from storage or creates a new session. The session is automatically
        committed if no exceptions occur, otherwise it is rolled back. The
        session is always closed when the context exits.

        :param session: An optional session object. If not provided, a session
            is retrieved from storage or a new one is created.
        :type session: Optional[Session]
        :yields: The active session for database operations.
        :raises Exception: Any exceptions raised during the session's execution
            will result in a rollback of the session.
        """

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
        """
        Returns the session storage object for the engine.

        The session storage object is used to store session objects for the
        engine. This allows the engine to maintain a consistent session
        object across different threads and contexts.

        Returns:
            The session storage object.
        """
        return self._session_storage

    def close_connection(self, conn):
        """
        Closes the provided connection.

        This method closes a database connection. It is typically used to
        release resources associated with the connection once database
        operations are completed.

        :param conn: The connection to be closed.
        :type conn: Connection object
        """

        conn.close()


class PgDictJsonbDumper(JsonbDumper):
    def dump(self, obj):
        return obj if obj is None else super().dump(Jsonb(obj))


class PgSQLEngine(AbstractEngine):

    URL_SCHEMA = c.RA_POSTGRESQL_PROTO_NAME
    DEFAULT_PORT = c.RA_POSTGRESQL_DB_PORT

    def __init__(self, db_url, config=None, query_cache=False):
        """
        Initializes the PostgreSQL engine.

        :param db_url: The connection URL for the PostgreSQL database.
        :param config: A dictionary of configuration options for the engine.
        :param query_cache: A boolean indicating whether the engine should
            cache query results.

        :return: The initialized engine.
        """

        super(PgSQLEngine, self).__init__(
            db_url=db_url,
            dialect=pgsql.PgSQLDialect(),
            session_storage=sessions.SessionThreadStorage(),
            config=config,
            query_cache=query_cache,
        )

        # RA expects the pool to be ready to use
        if not "open" in self._config:
            self._config["open"] = True

        self._pool = psycopg_pool.ConnectionPool(
            conninfo=db_url,
            configure=self._conn_configure_callback,
            **self._config,
        )
        self._pool.wait()

    def _conn_configure_callback(self, conn):
        conn.adapters.register_dumper(dict, PgDictJsonbDumper)

    def escape(self, value):
        """
        Escapes a value for use in a PostgreSQL query.

        This method is used by the :py:class:`PgSQLSession` class to escape
        values before they are used in a query. It is not intended to be used
        directly by applications.

        The value is escaped by wrapping it in double quotes. This is because
        double quotes are used to delimit strings in PostgreSQL, and the value
        is already escaped if it is a string.

        :param value: The value to be escaped.
        :return: The escaped value.
        """

        return '"' + value + '"'

    def __del__(self):
        """
        Closes the connection pool to the PostgreSQL database before the
        engine instance is garbage collected.

        This method is called when the engine instance is garbage collected
        to ensure that the connection pool is closed and any resources
        acquired by the pool are released.

        Note that the connection pool is not closed until the engine instance
        is garbage collected, which may not happen immediately. Therefore,
        this method is not suitable for use in applications where it is
        important to release resources immediately after they are no longer
        needed.

        :raises psycopg2.Error: If an error occurs while closing the pool.
        """

        self._pool.close()

    def get_session(self):
        """
        Creates and returns a new PgSQLSession instance for the current engine.

        This method initializes a session object that can be used to interact
        with the PostgreSQL database associated with this engine.

        :returns: A session object for database operations.
        :rtype: PgSQLSession
        """

        return sessions.PgSQLSession(engine=self)

    def get_connection(self):
        """
        Retrieves a connection from the pool.

        This method is used to acquire a PostgreSQL connection from the pool
        of connections managed by the engine. The connection is used to
        execute queries and other database operations.

        :returns: A connection object for database operations.
        :rtype: psycopg2.extensions.connection
        """

        return self._pool.getconn()

    def close_connection(self, conn):
        """
        Releases a connection back to the pool.

        This method runs appropriate cleanup routines and returns
        the connection back to the pool for reuse.

        :param conn: The connection to be released back to the pool.
        :type conn: psycopg2.extensions.connection
        """

        self._pool.putconn(conn)


class MySQLEngine(AbstractEngine):

    URL_SCHEMA = c.RA_MYSQL_PROTO_NAME
    DEFAULT_PORT = c.RA_MYSQL_DB_PORT

    def __init__(self, db_url, config=None, query_cache=False):
        """
        Initializes the MySQL engine.

        :param db_url: The URL of the database connection.
        :param config: A dictionary of configuration options for the engine.
        :param query_cache: A boolean indicating whether the engine should
            cache query results.

        :raises ValueError: If the database URL does not match the expected
            format.
        """
        super(MySQLEngine, self).__init__(
            db_url=db_url,
            dialect=mysql.MySQLDialect(),
            session_storage=sessions.SessionThreadStorage(),
            config=config,
            query_cache=query_cache,
        )

        if "connection_timeout" not in self._config:
            self._config["connection_timeout"] = DEFAULT_CONNECTION_TIMEOUT
        self._config.update(
            {
                "user": self.db_username,
                "password": self.db_password,
                "database": self.db_name,
                "host": self.db_host,
                "port": self.db_port,
                "converter_class": adapters.MySQLConverter,
            }
        )

        try:
            self._pool = pooling.MySQLConnectionPool(**self._config)
        except AttributeError as e:
            pool_name = e.args[0].split("'")[1]
            new_name = str(hash(pool_name))
            LOG.warning("Changing '%s' pool name to '%s'", pool_name, new_name)
            config["pool_name"] = new_name
            self._pool = pooling.MySQLConnectionPool(**self._config)

    def __del__(self):
        """
        Closes the connection pool to the MySQL database before the engine
        instance is garbage collected.

        This method is called when the engine instance is garbage collected to
        ensure that the connection pool is closed and any resources acquired by
        the pool are released.
        """
        pool = getattr(self, "_pool", None)
        if pool is not None:
            self._pool._remove_connections()

    def get_connection(self):
        """
        Retrieves a connection from the pool.

        This method is used to acquire a connection from the pool of
        connections managed by the engine. The connection is used to
        execute queries and other database operations.

        :returns: A connection object for database operations.
        :rtype: mysql.connector.connection.MySQLConnection
        """
        return self._pool.get_connection()

    def get_session(self):
        """
        Creates and returns a new MySQLSession instance for the current engine.

        This method initializes a session object that can be used to interact
        with the MySQL database associated with this engine.

        :returns: A session object for database operations.
        :rtype: MySQLSession
        """
        return sessions.MySQLSession(engine=self)


class EngineFactory(singletons.InheritSingleton):

    def __init__(self):
        """
        Initializes the engine factory singleton.

        This method is called when the singleton is created. It initializes the
        internal state of the factory by creating an empty dictionary to store
        engine instances and a mapping of database URLs to engine classes.

        :returns: None
        """
        super(EngineFactory, self).__init__()
        self._engines = {}
        self._engines_map = {
            MySQLEngine.URL_SCHEMA: MySQLEngine,
            PgSQLEngine.URL_SCHEMA: PgSQLEngine,
        }

    def configure_postgresql_factory(
        self,
        conf,
        section=c.DB_CONFIG_SECTION,
        name=DEFAULT_NAME,
    ):
        """
        Configures the engine factory for a PostgreSQL database.

        This method is a convenience wrapper around the `configure_factory`
        method that is specific to PostgreSQL databases. It takes the same
        parameters as `configure_factory` but provides default values for the
        configuration options that are specific to PostgreSQL.

        :param conf: The configuration object to read from.
        :param section: The section of the configuration object to read from.
        :param name: The name of the engine to configure.
        """
        self.configure_factory(
            db_url=conf[section].connection_url,
            config={
                "min_size": conf[section].connection_pool_min_size,
                "max_size": conf[section].connection_pool_max_size,
                "open": conf[section].connection_pool_open,
                "timeout": conf[section].connection_pool_client_timeout,
                "max_waiting": conf[section].connection_pool_max_waiting,
                "max_lifetime": conf[section].connection_max_lifetime,
                "max_idle": conf[section].connection_max_idle,
                "reconnect_timeout": conf[
                    section
                ].connection_pool_reconnect_timeout,
                "num_workers": conf[section].connection_pool_num_workers,
            },
            query_cache=conf[section].connection_query_cache,
            name=name,
        )

    def configure_mysql_factory(
        self,
        conf,
        section=c.DB_CONFIG_SECTION,
        name=DEFAULT_NAME,
    ):
        """
        Configures the engine factory for a MySQL database.

        This method is a convenience wrapper around the `configure_factory`
        method that is specific to MySQL databases. It takes the same
        parameters as `configure_factory` but provides default values for the
        configuration options that are specific to MySQL.

        :param conf: The configuration object to read from.
        :param section: The section of the configuration object to read from.
        :param name: The name of the engine to configure.
        """
        self.configure_factory(
            db_url=conf[section].connection_url,
            config={
                "pool_size": conf[section].connection_pool_size,
            },
            query_cache=conf[section].connection_query_cache,
            name=name,
        )

    def configure_factory(
        self,
        db_url,
        config=None,
        query_cache=False,
        name=DEFAULT_NAME,
    ):
        """
        Configures and creates a new database engine instance for the given
        URL.

        This method initializes a database engine based on the provided
        database URL, configuration options, and query caching preference. The
        initialized engine is stored in the factory's internal engines
        dictionary, keyed by the specified name.

        :param db_url: The database connection URL.
        :param config: A dictionary of configuration options for the engine.
                    Defaults to None.
        :param query_cache: A boolean indicating whether the engine should
                            cache query results. Defaults to False.
        :param name: The name under which to store the initialized engine in
                     the factory. Defaults to 'default'.

        :raises ValueError: If the schema from the db_url is not supported
                            or if no driver is found for the schema.
        """

        schema = db_url.split(":")[0]
        try:
            self._engines[name] = self._engines_map[schema.lower()](
                db_url=db_url, config=config, query_cache=query_cache
            )
        except KeyError:
            raise ValueError("Can not find driver for schema %s" % schema)

    def get_engine(self, name=DEFAULT_NAME):
        """
        Returns an engine instance from the factory's internal engines
        dictionary by name. If the specified engine name does not exist,
        a ValueError is raised.

        :param name: The name of the engine to return. Defaults to 'default'.
        :return: An engine instance.
        :raises ValueError: If the specified engine name is not found in the
                            factory's internal engines dictionary.
        """
        engine = self._engines.get(name, None)
        if engine:
            return engine
        raise ValueError(
            ("Can not return %s engine. Please configure EngineFactory")
            % name,
        )

    def destroy_engine(self, name=DEFAULT_NAME):
        """
        Removes and destroys the engine instance associated with the specified
        name from the factory's internal engines dictionary.

        This method attempts to delete the engine instance identified by the
        given name. If the engine instance does not exist, the method silently
        handles the KeyError exception.

        :param name: The name of the engine to destroy. Defaults to 'default'.
        """

        try:
            del self._engines[name]
        except KeyError:
            pass

    def destroy_all_engines(self):
        """
        Removes and destroys all engine instances from the factory's internal
        engines dictionary.

        This method resets the factory to its initial state, removing all
        configured engines. Subsequent calls to get_engine() will raise a
        ValueError until at least one engine is configured using
        configure_factory().
        """
        self._engines = {}


class DBConnectionUrl(object):

    _CENSORED = ":<censored>@"

    def __init__(self, db_url):
        """
        Initializes a DBConnectionUrl instance with the provided database URL.

        :param db_url: The URL of the database connection, which will be
                       parsed and stored.
        """

        super(DBConnectionUrl, self).__init__()
        self._db_url = parse.urlparse(db_url)

    def __repr__(self):
        """
        Returns a string representation of the DBConnectionUrl instance.

        The string representation is generated by replacing the password
        substring in the original URL with the value of _CENSORED, to prevent
        the password from being displayed.

        :return: A string representation of the DBConnectionUrl instance.
        """
        if self._db_url.password is None:
            orig_substr = "@"
        else:
            orig_substr = ":%s@" % self._db_url.password
        return self.url.replace(orig_substr, self._CENSORED)

    @property
    def url(self):
        """
        Returns the full URL string of the database connection.

        This property retrieves the complete URL by converting the parsed
        URL components back into a string representation. It is useful for
        obtaining the original connection URL, with the password censored
        if applicable, after it has been parsed and stored.
        """

        return self._db_url.geturl()


engine_factory = EngineFactory()
