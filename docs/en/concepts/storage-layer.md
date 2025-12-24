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

# Storage layer

The storage layer in RESTAlchemy is responsible for persisting DM models and retrieving them back.

It is built as a separate layer on top of the Data Model (DM) layer and below the API layer.

---

## Modules overview

Main modules involved in SQL storage:

- `restalchemy.storage.base`
  - Abstract interfaces for storable models and collections.
- `restalchemy.storage.exceptions`
  - Storage-level exceptions.
- `restalchemy.storage.sql.engines`
  - Engine factory and SQL engine implementations (MySQL, PostgreSQL).
- `restalchemy.storage.sql.sessions`
  - Database sessions, transactions, and per-session query cache.
- `restalchemy.storage.sql.orm`
  - ORM-like mixins and collections (`SQLStorableMixin`, `ObjectCollection`).
- `restalchemy.storage.sql.tables`
  - Table abstraction used by ORM and dialects.
- `restalchemy.storage.sql.dialect.*`
  - Dialect-specific query builders for MySQL and PostgreSQL.

You usually interact only with:

- DM models + `orm.SQLStorableMixin`;
- `engines.engine_factory.configure_factory()` to configure the engine;
- model class attributes like `__tablename__` and class-level `objects` collection.

---

## High-level architecture

### 1. DM model

You define a DM model that inherits from:

- `models.ModelWithUUID` (or another `Model*` base), and
- `orm.SQLStorableMixin`.

Example (simplified from `examples/dm_mysql_storage.py`):

```python
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "bars"
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

### 2. Engine and sessions

`restalchemy.storage.sql.engines` contains an `engine_factory` that manages SQL engines.

Typical configuration:

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/mydb",
)
```

Key ideas:

- **Engine** parses `db_url`, configures a connection pool and dialect.
- **Session** (`PgSQLSession` / `MySQLSession`) is created by the engine and used to execute queries.
- `session_manager(engine, session=None)` in `sessions.py` wraps session usage into a transaction boundary.

### 3. ORM mixins and collections

`restalchemy.storage.sql.orm` provides:

- `SQLStorableMixin` — mixin for DM models that should be stored in SQL.
- `ObjectCollection` — collection API, exposed as `Model.objects`.

Responsibilities:

- **`SQLStorableMixin`**:
  - Binds the DM model to a SQL table via `__tablename__` and `get_table()`.
  - Implements `insert()`, `save()`, `update()`, `delete()`.
  - Converts DM properties to SQL storable values and back.

- **`ObjectCollection`**:
  - Provides `get_all()`, `get_one()`, `get_one_or_none()`, `query()`, `count()`.
  - Uses filters (`restalchemy.dm.filters`) to express WHERE conditions.

### 4. Dialects and tables

Dialect modules (`restalchemy.storage.sql.dialect.*`) and `tables.SQLTable` are internal helpers that:

- Build SQL statements (SELECT/INSERT/UPDATE/DELETE).
- Bind parameters.
- Execute queries via sessions.

As a user, you rarely need to touch them directly — they are driven by models and collections.

---

## Lifecycle of a SQL-backed model

1. **Define model**
   - Inherit from `ModelWithUUID` and `SQLStorableMixin`.
   - Specify `__tablename__`.
   - Declare fields with DM properties and types.

2. **Configure engine**
   - Call `engine_factory.configure_factory(db_url=...)` once at startup.

3. **Create tables / run migrations**
   - Use the migration tooling (`ra-new-migration`, `ra-apply-migration`) to create/update the actual database schema.

4. **Perform CRUD operations**
   - Create model instances and call `.save()`.
   - Use `Model.objects.get_all()` / `.get_one(filters=...)` to read data.
   - Call `.delete()` to remove records.

5. **Use filters and expressions**
   - Build filters with `restalchemy.dm.filters` and pass them to `objects.get_all()` / `objects.get_one()`.

6. **Transactions and sessions (optional)**
   - Wrap groups of operations in an explicit session using `session_manager()` when you need fine-grained control over transactions.

All of these steps are demonstrated concretely in the DM+SQL how-to and in `examples/dm_mysql_storage.py` and `examples/dm_pg_storage.py`.
