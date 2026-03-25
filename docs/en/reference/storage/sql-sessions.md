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

# SQL sessions and transactions

Module: `restalchemy.storage.sql.sessions`

This module defines session classes for PostgreSQL and MySQL, query caching, and helpers for managing sessions.

---

## SessionQueryCache

`SessionQueryCache` is a per-session cache for query results.

- Computes a hash based on the SQL statement and bound values.
- Stores results of `get_all()` and `query()`.
- Reuses cached results when the same query is executed again within the same session.

Used internally by `PgSQLSession` and `MySQLSession` when `cache=True`.

---

## PgSQLSession

`PgSQLSession` wraps a PostgreSQL connection and cursor:

- Obtains connections from `PgSQLEngine` via `engine.get_connection()`.
- Uses a row factory (`pg_rows.dict_row`) to get dict-like rows.
- Exposes `execute()`, `execute_many()`, `commit()`, `rollback()`, `close()`.
- Provides `batch_insert(models)` and `batch_delete(models)` helpers:
  - Ensure all models are of the same type.
  - Build bulk SQL operations via `pgsql` dialect classes.

The session is usually managed by:

- `engine.session_manager()` from `AbstractEngine`, or
- `session_manager(engine, session=None)` context manager from this module.

---

## MySQLSession

`MySQLSession` is similar to `PgSQLSession`, but uses:

- MySQL connections obtained from `MySQLEngine`.
- `mysql.connector` cursors with `dictionary=True`.
- `mysql` dialect classes (`MySQLInsert`, `MySQLBatchDelete`, etc.).

It also supports:

- `batch_insert(models)` and `batch_delete(models)`.
- Exception translation for common deadlock and integrity errors into storage exceptions.

---

## session_manager

There are two related mechanisms for session management:

1. `engines.AbstractEngine.session_manager()`
2. `sessions.session_manager(engine, session=None)`

`engines.AbstractEngine.session_manager()`:

- Used most often.
- If no session is provided, it:
  - Creates a new session via `engine.get_session()`.
  - Yields it to the caller.
  - Commits on success, rolls back on exception.
  - Closes the session at the end.
- If a session is provided, it simply yields it without additional handling.

`sessions.session_manager(engine, session=None)`:

- Similar behavior, implemented in the sessions module.
- Can be used directly if you already have an engine instance.

Example:

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    # Perform multiple operations within a single transaction
    foo = FooModel(foo_field1=42)
    foo.save(session=session)
```

---

## SessionThreadStorage

`SessionThreadStorage` is a thread-local storage for sessions:

- Stores a single session per thread.
- Provides methods:
  - `get_session()` — returns the stored session or raises `SessionNotFound`.
  - `store_session(session)` — stores a session for the current thread, raising `SessionConflict` if one is already stored.
  - `remove_session()` / `pop_session()` — clear or retrieve-and-clear the stored session.

Engines use `SessionThreadStorage` as their session storage so that:

- A session can be created once and reused by multiple operations in the same thread.
- Higher-level code can integrate RESTAlchemy sessions into existing transaction management.
