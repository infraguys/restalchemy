<!--
Copyright 2025 Genesis Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# SQL engines

Module: `restalchemy.storage.sql.engines`

This module contains the engine factory and concrete SQL engine implementations for MySQL and PostgreSQL.

---

## AbstractEngine

`AbstractEngine` defines the common behavior for all SQL engines:

- Parses the database URL.
- Exposes database name, host, port, username and password.
- Holds the SQL dialect (`mysql.MySQLDialect` or `pgsql.PgSQLDialect`).
- Provides a `session_manager()` context manager.

Key properties and methods:

- `URL_SCHEMA` (abstract): expected URL schema, e.g. `"mysql"`, `"postgresql"`.
- `DEFAULT_PORT` (abstract): port used if not specified in URL.
- `db_name`, `db_username`, `db_password`, `db_host`, `db_port`.
- `dialect`: the SQL dialect object.
- `query_cache`: whether session-level query cache is enabled.
- `get_connection()`: obtain a connection (implemented by subclasses).
- `get_session()`: obtain a session object (implemented by subclasses).
- `session_manager(session=None)`: context manager that manages commit/rollback and closing the session.
- `get_session_storage()`: returns the session storage (`SessionThreadStorage`).

Example:

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()
print(engine.db_name)
```

---

## PostgreSQL engine

### `PgSQLEngine`

- `URL_SCHEMA = "postgresql"`.
- `DEFAULT_PORT` is taken from `restalchemy.common.constants.RA_POSTGRESQL_DB_PORT`.
- Uses `psycopg_pool.ConnectionPool` for connections.
- Dialect: `pgsql.PgSQLDialect()`.
- Session type: `sessions.PgSQLSession`.

Constructor:

```python
PgSQLEngine(db_url, config=None, query_cache=False)
```

- `db_url`: PostgreSQL connection URL.
- `config`: passed to `psycopg_pool.ConnectionPool`.
- `query_cache`: enables query caching.

Methods:

- `get_session()`: returns `PgSQLSession(engine=self)`.
- `get_connection()`: gets a connection from the pool.
- `close_connection(conn)`: returns the connection back to the pool.

The engine is created internally by `EngineFactory`.

---

## MySQL engine

### `MySQLEngine`

- `URL_SCHEMA = "mysql"`.
- `DEFAULT_PORT` is taken from `RA_MYSQL_DB_PORT`.
- Uses `mysql.connector.pooling.MySQLConnectionPool`.
- Dialect: `mysql.MySQLDialect()`.
- Session type: `sessions.MySQLSession`.

Constructor:

```python
MySQLEngine(db_url, config=None, query_cache=False)
```

- `db_url`: MySQL connection URL.
- `config`: pool configuration.
- `query_cache`: enables query caching.

Methods:

- `get_connection()`: returns a connection from the pool.
- `get_session()`: returns `MySQLSession(engine=self)`.

---

## EngineFactory and engine_factory

### `EngineFactory`

A singleton responsible for configuring and storing engine instances.

Important methods:

- `configure_factory(db_url, config=None, query_cache=False, name="default")`
  - Creates an engine instance based on `db_url` and stores it under `name`.
  - Infers engine class from URL schema ("mysql", "postgresql").
- `configure_postgresql_factory(conf, section, name)`
  - Helper for configuring PostgreSQL from a config object.
- `configure_mysql_factory(conf, section, name)`
  - Helper for configuring MySQL from a config object.
- `get_engine(name="default")`
  - Returns the configured engine instance.
- `destroy_engine(name="default")` / `destroy_all_engines()`
  - Remove engines from the factory.

At module level:

```python
engine_factory = EngineFactory()
```

Most applications use this singleton:

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(db_url="mysql://...")
engine = engines.engine_factory.get_engine()
```

---

## DBConnectionUrl

`DBConnectionUrl` is a small helper that parses a DB URL and provides a censored string representation.

- Stores the parsed URL.
- `url` property returns the full URL string.
- `__repr__` hides the password by replacing it with `:<censored>@`.

This is mainly useful for logging and debugging.
