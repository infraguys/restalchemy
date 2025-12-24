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

# Properties

Module: `restalchemy.dm.properties`

Properties are the core mechanism used by DM models to define and store field values.

---

## Core classes

### `AbstractProperty`

Base abstract interface for all properties:

- `value` (property): get/set the current value.
- `set_value_force(value)`: assign a value bypassing read-only and ID checks.
- `is_dirty()`: check if the value has changed since initialization.
- `is_prefetch()` (class method): whether the property participates in prefetching.

### `Property`

The main implementation for scalar and structured fields.

Constructor:

```python
Property(
    property_type,
    default=None,
    required=False,
    read_only=False,
    value=None,
    mutable=False,
    example=None,
)
```

Key behavior:

- `property_type` must be an instance of `types.BaseType`.
- `default` may be a value or a callable; for callables it is evaluated once.
- If `value` is provided, it overrides `default`.
- If `mutable=False`, the initial value is deep-copied for dirty tracking.
- `is_required()` and `is_read_only()` describe validation rules.
- Assigning invalid values raises `TypeError` from `restalchemy.common.exceptions`.

ID properties are represented by `IDProperty`, which simply overrides `is_id_property()`.

### `IDProperty`

Specialization of `Property` used for ID fields:

- `is_id_property()` returns `True`.
- Combined with `ModelWithID`/`ModelWithUUID` to identify primary key fields.

---

## PropertyCreator and factories

### `PropertyCreator`

`PropertyCreator` is a lightweight factory that stores how to construct a concrete property instance:

- Holds the property class (`Property` or `IDProperty`).
- Holds the DM type instance (e.g. `types.String()`).
- Stores positional and keyword arguments used to build the property.
- `is_prefetch()` reflects the `prefetch` flag (used with relationships).

Instances of `PropertyCreator` are what you actually assign to model class attributes.

### `property()`

The main factory function used in models:

```python
from restalchemy.dm import properties, types


class Foo(models.Model):
    value = properties.property(types.Integer(), required=True)
```

Arguments:

- `property_type`: instance of `types.BaseType`.
- `id_property`: if `True`, uses `IDProperty`.
- `property_class`: custom property class (must inherit from `AbstractProperty`).
- Other keyword arguments are passed to the property constructor (`default`, `required`, `read_only`, `mutable`, `example`, etc.).

Returns:

- A `PropertyCreator` that will create `Property`/`IDProperty` instances when the model is instantiated.

### Convenience factories

- `required_property(property_type, *args, **kwargs)` — sets `required=True`.
- `readonly_property(property_type, *args, **kwargs)` — sets `read_only=True` and `required=True`.

Example:

```python
class User(models.ModelWithUUID):
    email = properties.required_property(types.Email())
    created_at = properties.readonly_property(types.UTCDateTimeZ(), default=datetime.datetime.now)
```

---

## Property collections and managers

### `PropertyCollection`

A collection of property definitions used by `MetaModel`.

- Stores a mapping of field names to `PropertyCreator` (or nested `PropertyCollection`).
- Implements mapping protocol (`__getitem__`, `__iter__`, `__len__`).
- `sort_properties()` can be used to sort fields by name (useful in tests).
- `instantiate_property(name, value=None)` constructs a concrete property instance.

`Model.properties` is a `PropertyCollection` at the class level.

### `PropertyManager`

A runtime container used at instance level:

- Constructed from a `PropertyCollection` and keyword arguments.
- Builds actual property objects (or nested `PropertyManager` for containers).
- Exposes `properties` (a read-only mapping of property instances).
- Exposes `value` as a dict of raw values (read/write).

`Model.pour()` uses `PropertyManager` to build instance state:

```python
self.properties = properties.PropertyManager(self.properties, **kwargs)
```

If a required property is missing, `PropertyManager` raises `PropertyRequired` with the field name.

---

## Containers and nested structures

### `container()`

Creates a nested `PropertyCollection` for grouping related fields:

```python
address_container = properties.container(
    city=properties.property(types.String()),
    zip_code=properties.property(types.String()),
)


class User(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)
    address = address_container
```

At runtime, `address` becomes a nested `PropertyManager`, and you can access:

```python
user.address.value["city"]
user.address.value["zip_code"]
```

Nested containers are especially useful for complex JSON structures and OpenAPI schemas.

---

## Dirty tracking

Both `Property` and `Relationship` support `is_dirty()`:

- `Property` compares the current value to the initial one.
- `Relationship` compares the current related object to the initial one.

`Model.is_dirty()` iterates over all properties and returns `True` if any of them is dirty. This is heavily used by storage layers to decide whether updates are needed.

---

## Best practices

- Always use DM `types.*` rather than raw Python types inside properties.
- Mark ID fields with `id_property=True` or use helper models (`ModelWithUUID`).
- Prefer `required_property()` and `readonly_property()` for clarity when appropriate.
- Use `container()` for logically grouped fields or nested JSON data.
