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

# DM models

Module: `restalchemy.dm.models`

This module defines the base classes and mixins for data models in RESTAlchemy.

---

## MetaModel and Model

### `MetaModel`

`MetaModel` is a metaclass used by all DM models. It:

- Collects field definitions created with `properties.property()` and `properties.container()`.
- Merges properties from base classes.
- Tracks ID properties in `id_properties`.
- Attaches an operational storage (`__operational_storage__`) for per-model auxiliary data.

You normally do not use `MetaModel` directly; you inherit from `Model` or its subclasses.

### `Model`

`Model` is the fundamental base class for DM models:

```python
from restalchemy.dm import models, properties, types


class Foo(models.Model):
    foo_id = properties.property(types.Integer(), id_property=True, required=True)
    name = properties.property(types.String(max_length=255), default="")
```

Key behavior:

- The constructor accepts keyword arguments and passes them to `pour()`.
- `pour()` builds a `PropertyManager` from the model's `properties` collection, validates required fields and types.
- Attribute access is mapped to properties:
  - `model.field` reads `properties[field].value`.
  - `model.field = value` sets and validates the value.
- `as_plain_dict()` returns a plain dictionary representation of the model values.
- The model behaves as an immutable mapping over its properties (`__getitem__`, `__iter__`, `__len__`).

Error handling:

- If you assign a value of the wrong type, a `ModelTypeError` is raised.
- If you omit a required property, a `PropertyRequired` error is raised.
- If you attempt to change a read-only property or ID property, a `ReadOnlyProperty` error is raised.

Overriding validation:

```python
class PositiveFoo(models.Model):
    value = properties.property(types.Integer(), required=True)

    def validate(self):
        if self.value <= 0:
            raise ValueError("value must be positive")
```

`validate()` is called from `pour()` after properties are constructed.

---

## ID handling

### `ModelWithID`

`ModelWithID` extends `Model` with convenience methods for models that have exactly one ID property:

- `get_id()` returns the current value of the ID property.
- Equality and hashing are based on `get_id()`.

If a model has zero or multiple ID properties, `get_id_property()` raises a `TypeError`, and you should override ID logic yourself.

### `ModelWithUUID` and `ModelWithRequiredUUID`

`ModelWithUUID` defines a UUID primary key:

```python
class ModelWithUUID(ModelWithID):
    uuid = properties.property(
        types.UUID(),
        read_only=True,
        id_property=True,
        default=lambda: uuid.uuid4(),
    )
```

Usage example:

```python
class Foo(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)

foo = Foo(value=10)
print(foo.uuid)       # auto-generated UUID
print(foo.get_id())   # same as foo.uuid
```

`ModelWithRequiredUUID` is similar, but the UUID must be provided explicitly instead of defaulting to a generated value.

---

## Operational storage

### `DmOperationalStorage`

A small helper used by `MetaModel` as `__operational_storage__` for each model class:

- `store(name, data)` — store arbitrary data by name.
- `get(name)` — retrieve data, raising `NotFoundOperationalStorageError` if missing.

Example:

```python
from restalchemy.dm import models


class Foo(models.ModelWithUUID):
    pass

# Store some per-model metadata
Foo.__operational_storage__.store("table_name", "foos")

assert Foo.__operational_storage__.get("table_name") == "foos"
```

This storage is intended for framework internals and advanced extensions.

---

## Common mixins

### `ModelWithTimestamp`

Adds `created_at` and `updated_at` fields with UTC timestamps:

- Both fields are required, read-only and use `types.UTCDateTimeZ()`.
- `update()` automatically refreshes `updated_at` when the model is dirty (or when `force=True`).

Typical use:

```python
class TimestampedFoo(models.ModelWithUUID, models.ModelWithTimestamp):
    value = properties.property(types.Integer(), required=True)
```

### `ModelWithProject`

Adds a required, read-only `project_id` field of type `types.UUID()`.

```python
class ProjectResource(models.ModelWithUUID, models.ModelWithProject):
    name = properties.property(types.String(max_length=255), required=True)
```

### `ModelWithNameDesc` and `ModelWithRequiredNameDesc`

Provide common `name` and `description` fields:

- `ModelWithNameDesc`:
  - `name`: string up to 255 characters, default `""`.
  - `description`: string up to 255 characters, default `""`.
- `ModelWithRequiredNameDesc`:
  - `name` is required.

These mixins are handy for many domain objects that need consistent naming.

---

## Custom properties and simple views

### `CustomPropertiesMixin`

Allows defining additional, non-static "custom properties" with their own types:

- `__custom_properties__`: a mapping of property names to DM types (`types.BaseType` subclasses).
- `get_custom_properties()` yields `(name, type)` pairs.
- `get_custom_property_type(name)` returns the type for a custom property.
- `_check_custom_property_value()` validates and optionally enforces static values.

This is an advanced feature and typically used together with the simple view mixins.

### `DumpToSimpleViewMixin`

Provides `dump_to_simple_view()` to convert a model into a structure of simple Python types (suitable for JSON, OpenAPI, storage):

```python
result = model.dump_to_simple_view(
    skip=["internal_field"],
    save_uuid=True,
    custom_properties=False,
)
```

Behavior:

- Iterates over `self.properties` and converts each value using the underlying DM type's `to_simple_type()`.
- If `save_uuid=True`, UUID fields (including `AllowNone(UUID)`) are serialized as raw UUID strings.
- If `custom_properties=True` (or the model has `__custom_properties__`), also converts custom properties.

### `RestoreFromSimpleViewMixin`

Provides `restore_from_simple_view()` for constructing a model from a simple structure:

```python
user = User.restore_from_simple_view(
    skip_unknown_fields=True,
    name="Alice",
    created_at="2006-01-02T15:04:05.000576Z",
)
```

Behavior:

- Normalizes field names (replaces `-` with `_`).
- Optionally skips unknown fields.
- Uses the DM type's `from_simple_type()` or `from_unicode()` to convert values.

### `SimpleViewMixin`

A convenience mixin combining both behaviors:

```python
class User(models.ModelWithUUID, models.SimpleViewMixin):
    name = properties.property(types.String(max_length=255), required=True)
```

You can then round-trip a model through a simple view:

```python
plain = user.dump_to_simple_view()
user2 = User.restore_from_simple_view(**plain)
```

---

## Summary

- Use `Model` (or helper base classes) as a foundation for all DM models.
- Use mixins like `ModelWithUUID`, `ModelWithTimestamp`, `ModelWithProject`, `ModelWithNameDesc` to avoid repeating common patterns.
- Use the simple view mixins to convert models to/from plain data structures when integrating with APIs, OpenAPI or external storage.
