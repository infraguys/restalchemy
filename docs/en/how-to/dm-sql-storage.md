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

# DM + SQL storage how-to

This guide shows how to persist DM models into a SQL database using RESTAlchemy.

You will:

- Define DM models with `ModelWithUUID` and `SQLStorableMixin`.
- Configure a SQL engine (MySQL or PostgreSQL).
- Create and query data using `.save()`, `.delete()` and `Model.objects`.
- Use filters for queries.

Examples are based on `examples/dm_mysql_storage.py` and `examples/dm_pg_storage.py`.

---

## Prerequisites

- RESTAlchemy installed (see `installation.md`).
- A running database:
  - MySQL or MariaDB, or
  - PostgreSQL.
- Appropriate Python driver installed, for example:
  - `mysql-connector-python` for MySQL.
  - `psycopg[binary]` for PostgreSQL.
- Tables created according to the model definitions (see the migration section below).

---

## 1. Define DM models for SQL

The minimal pattern for a SQL-backed model is:

- Inherit from `models.ModelWithUUID` (or another `ModelWithID`).
- Inherit from `orm.SQLStorableMixin`.
- Set `__tablename__` to the table name.
- Declare DM properties with types.

Example (simplified from `dm_mysql_storage.py`):

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

These models use DM validation and relationships while `SQLStorableMixin` adds persistence methods.

---

## 2. Configure the SQL engine

Use `restalchemy.storage.sql.engines.engine_factory` to create an engine instance.

### MySQL example

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/test",
)
```

### PostgreSQL example

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="postgresql://postgres:password@127.0.0.1:5432/ra_tests",
)
```

You should call `configure_factory()` once during application startup. Later, all models using `SQLStorableMixin` will obtain the engine via `engine_factory.get_engine()`.

Optional arguments:

- `config` — engine-specific configuration (pool sizes, timeouts, etc.).
- `query_cache` — enable per-session query cache.

---

## 3. Create tables and run migrations

RESTAlchemy does not auto-create tables; instead, it relies on explicit migrations.

Use the migration commands described in `README.rst`:

- `ra-new-migration` — create new migration files.
- `ra-apply-migration` — apply migrations to the target database.

The examples include commented SQL schemas, for example in `dm_mysql_storage.py`:

```sql
CREATE TABLE `foos` (
     `uuid` CHAR(36) NOT NULL,
     `foo_field1` INT NOT NULL,
     `foo_field2` VARCHAR(255) NOT NULL,
 PRIMARY KEY (`uuid`)
) ENGINE = InnoDB;

CREATE TABLE `bars` (
    `uuid` CHAR(36) NOT NULL,
    `bar_field1` VARCHAR(10) NOT NULL,
    `foo` CHAR(36) NOT NULL,
    CONSTRAINT `_idx_foo` FOREIGN KEY (`foo`) REFERENCES `foos`(`uuid`)
) ENGINE = InnoDB;
```

You can adapt these schemas to your environment or generate migrations that produce similar DDL.

---

## 4. Basic CRUD operations

Once the engine is configured and tables exist, you can use the DM models as persistent entities.

### Create and save

```python
foo1 = FooModel(foo_field1=10)
foo1.save()  # INSERT into foos

bar1 = BarModel(bar_field1="test", foo=foo1)
bar1.save()  # INSERT into bars
```

### Read data

```python
# All bars
all_bars = list(BarModel.objects.get_all())

# One bar by primary key
same_bar = BarModel.objects.get_one(filters={"uuid": bar1.get_id()})

# All bars for a given FooModel instance
bars_for_foo = list(BarModel.objects.get_all(filters={"foo": foo1}))

# Convert to plain dict
print(bar1.as_plain_dict())
```

### Update

```python
foo2 = FooModel(foo_field1=11, foo_field2="some text")
foo2.save()

# Modify and save again (UPDATE)
foo2.foo_field2 = "updated text"
foo2.save()
```

If a model is already saved, `save()` calls `update()`. Otherwise, it calls `insert()`.

### Delete

```python
for foo in FooModel.objects.get_all():
    foo.delete()
```

This issues `DELETE` statements based on the model's ID properties.

---

## 5. Filtering

Filters are defined in `restalchemy.dm.filters` and can be passed to `get_all()` and `get_one()`.

### Simple filters

```python
from restalchemy.dm import filters

# foo_field1 == 10
one = FooModel.objects.get_one(filters={"foo_field1": filters.EQ(10)})

# foo_field1 > 5
greater = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.GT(5)})
)

# foo_field1 IN (5, 6)
subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.In([5, 6])})
)

# foo_field1 NOT IN (1, 2)
not_subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.NotIn([1, 2])})
)
```

### Complex expressions

You can build complex conditions with `AND` and `OR` expressions:

```python
from restalchemy.dm import filters

# WHERE ((foo_field1 = 1 AND foo_field2 = '2') OR (foo_field2 = '3'))
filter_expr = filters.OR(
    filters.AND(
        {
            "foo_field1": filters.EQ(1),
            "foo_field2": filters.EQ("2"),
        }
    ),
    filters.AND({"foo_field2": filters.EQ("3")}),
)

foo = FooModel.objects.get_one(filters=filter_expr)
```

The storage layer translates these filter structures into SQL WHERE clauses.

---

## 6. Transactions and explicit sessions

By default, each operation uses an internal session and transaction.

If you need to group multiple operations in a single transaction, use `engine.session_manager()` or `sessions.session_manager()`.

### Using engine.session_manager()

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    foo = FooModel(foo_field1=42)
    foo.save(session=session)

    bar = BarModel(bar_field1="x", foo=foo)
    bar.save(session=session)
    # If any error happens here, both INSERTs are rolled back.
```

Inside the `with` block, all operations share the same session and transaction.

You can also reuse a session object obtained from the engine elsewhere in your code by passing `session=` to `.save()`, `.delete()` or collection methods.

---

## Summary

- Define DM models with `ModelWithUUID` + `SQLStorableMixin` and a `__tablename__`.
- Configure a SQL engine via `engine_factory.configure_factory()`.
- Use migrations to create/update the underlying tables.
- Use `.save()`, `.delete()` and `Model.objects.get_all() / get_one()` to perform CRUD operations.
- Use DM filters to express query conditions.
- Use explicit sessions and transactions when you need more control.
