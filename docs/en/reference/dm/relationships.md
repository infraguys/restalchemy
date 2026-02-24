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

# Relationships

Module: `restalchemy.dm.relationships`

Relationships connect DM models to each other.

---

## Relationship factories

### `relationship(property_type, *args, **kwargs)`

Main factory for defining relationships inside DM models.

Arguments:

- `property_type`: the related model class (subclass of `models.Model`).
- Positional `*args`: typically model classes used for validation.
- Keyword arguments:
  - `prefetch`: if `True`, uses `PrefetchRelationship` as property class.
  - `required`, `read_only`, `default`, etc.

Under the hood this function:

- Verifies that all positional arguments are DM model classes.
- Chooses the property class:
  - `PrefetchRelationship` when `prefetch=True`.
  - `Relationship` otherwise.
- Delegates to `properties.property()` with appropriate `property_class`.

### `required_relationship(property_type, *args, **kwargs)`

Same as `relationship()`, but sets `required=True`.

### `readonly_relationship(property_type, *args, **kwargs)`

Same as `required_relationship()`, but also sets `read_only=True`.

---

## Relationship classes

### `Relationship`

A property representing a single related model instance.

Constructor parameters mirror scalar `Property`, but `property_type` is a model class:

- `property_type`: DM model class.
- `default`, `required`, `read_only`, `value`.

Behavior:

- Accepts `None` or an instance of `property_type`.
- Enforces `required` and `read_only` flags.
- Tracks `is_dirty()` by comparing current value with the initial value.
- Exposes `property_type` (`get_property_type()` returns the model class).

If you pass a value of the wrong type, a `TypeError` is raised.

### `PrefetchRelationship`

Subclass of `Relationship` used when `prefetch=True`:

- Overrides `is_prefetch()` class method to return `True`.
- Otherwise behaves like `Relationship`.

Prefetch flags are typically used by storage or API layers to optimize data loading.

---

## Example: one-to-many via DM + API

Below is a simplified version of the `Foo`/`Bar` relationship used in examples.

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)


class BarModel(models.ModelWithUUID):
    # Simple string field
    name = properties.property(types.String(max_length=10), required=True)

    # Link to a FooModel instance
    foo = relationships.relationship(FooModel)
```

Now you can work with relationships as normal attributes:

```python
foo = FooModel(value=10)
bar = BarModel(name="test", foo=foo)

assert bar.foo is foo
```

Combined with storage (see DM + SQL examples), relationships can be used to express foreign keys and joins.

---

## Example: required and read-only relationships

```python
class ReadOnlyBar(models.ModelWithUUID):
    foo = relationships.readonly_relationship(FooModel)
```

- The `foo` relationship must always be set (required).
- It cannot be changed after initialization (read-only), unless you use `set_value_force()` at a lower level.

---

## Best practices

- Use relationships for DM-level modeling of links between entities; actual foreign keys and joins are handled by the storage layer.
- Keep relationships simple: one model field usually represents one logical relation.
- Use `prefetch=True` only when you need to hint storage/API layers about preloading behavior.
