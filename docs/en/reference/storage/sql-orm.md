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

# SQL ORM mixins and collections

Module: `restalchemy.storage.sql.orm`

This module provides ORM-like behavior for DM models:

- `ObjectCollection` — collection API exposed as `Model.objects`.
- `SQLStorableMixin` — mixin that adds `save()`, `update()`, `delete()` and integration with SQL tables.
- `SQLStorableWithJSONFieldsMixin` — specialization for models with JSON fields.

---

## ObjectCollection

`ObjectCollection` implements the collection interface for SQL-backed models.

Key methods:

- `get_all(filters=None, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - Returns a list of model instances.
  - Uses `filters` (DM filter structures) to build WHERE clauses.
  - Can use per-session query cache when `cache=True`.
- `get_one(filters=None, session=None, cache=False, locked=False)`
  - Returns exactly one model instance.
  - Raises `RecordNotFound` if no rows, `HasManyRecords` if more than one.
- `get_one_or_none(filters=None, session=None, cache=False, locked=False)`
  - Returns a single instance or `None` if not found.
- `query(where_conditions, where_values, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - Executes a custom WHERE clause.
- `count(session=None, filters=None)`
  - Returns the number of rows matching filters.

`ObjectCollection` uses:

- The SQL dialect via `engine.dialect`.
- The model's `restore_from_storage()` method to convert rows into DM models.

---

## SQLStorableMixin

`SQLStorableMixin` is intended to be combined with DM models to make them storable in SQL.

### Requirements

- The DM model must have a valid `__tablename__` string.
- There must be at least one ID property (`id_property=True`).

### Core responsibilities

- `get_table()`
  - Returns a `SQLTable` instance for the model, cached in `__operational_storage__`.
- `insert(session=None)`
  - Inserts the model into the table using current property values.
  - Wraps dialect-specific exceptions into storage exceptions (e.g. conflicts).
- `save(session=None)`
  - If the instance is not yet saved, calls `insert()`.
  - Otherwise calls `update()`.
- `update(session=None, force=False)`
  - Updates the row when the model is dirty or `force=True`.
  - Validates the model before updating.
  - Ensures exactly one row is updated (otherwise raises).
- `delete(session=None)`
  - Deletes the row corresponding to the model's ID properties.
- `restore_from_storage(**kwargs)` (class method)
  - Converts database row values (simple types) to DM property values.
  - Constructs a model instance marked as saved.

### Object collection binding

`SQLStorableMixin` defines `_ObjectCollection = ObjectCollection`. In combination with base storage classes this provides:

- `Model.objects` — a collection that uses `ObjectCollection` to perform queries.

### Type conversion helpers

- `to_simple_type(value)` (class method)
  - Converts model instances or raw ID values to a form suitable for filters.
- `from_simple_type(value)` (class method)
  - Converts raw ID values or prefetch results into model instances.

These helpers allow storage and API layers to work with IDs and prefetch structures transparently.

---

## SQLStorableWithJSONFieldsMixin

`SQLStorableWithJSONFieldsMixin` extends `SQLStorableMixin` for databases that do not support JSON fields natively.

Usage pattern:

- Inherit from `SQLStorableWithJSONFieldsMixin` instead of `SQLStorableMixin`.
- Define `__jsonfields__` as an iterable of field names that store JSON data.

Behavior:

- `restore_from_storage()`
  - For fields listed in `__jsonfields__`:
    - If the stored value is a string, parses it as JSON.
- `_get_prepared_data(properties=None)`
  - For fields in `__jsonfields__`, dumps Python data structures to compact JSON strings.

This allows you to keep JSON fields in your DM models while persisting them as text in databases that lack native JSON support.
