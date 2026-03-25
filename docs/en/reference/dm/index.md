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

# Data Model (DM) reference

This section describes the core Data Model (DM) layer in RESTAlchemy.

The DM layer is responsible for:

- Declaring domain models as Python classes.
- Defining fields, types and validation rules.
- Expressing relationships between models.
- Providing helper mixins for common patterns (UUID IDs, timestamps, names, etc.).

The DM layer is implemented in the following modules:

- `restalchemy.dm.models`
- `restalchemy.dm.properties`
- `restalchemy.dm.relationships`
- `restalchemy.dm.types`
- `restalchemy.dm.filters`
- `restalchemy.dm.types_dynamic` (advanced types)
- `restalchemy.dm.types_network` (network-related types)

This reference focuses on the first five modules, which you will use most of the time.

---

## Quick overview

A typical DM model is defined like this:

```python
from restalchemy.dm import models, properties, types


class Foo(models.ModelWithUUID):
    # Integer field, required
    value = properties.property(types.Integer(), required=True)

    # Optional string with default value
    description = properties.property(types.String(max_length=255), default="")
```

Key ideas:

- You inherit from `Model` or one of the helper base classes such as `ModelWithUUID`.
- You use `properties.property()` to declare fields.
- You use `types.*` classes to describe the type and constraints of each field.

Relationships between models are declared via `relationships.relationship()`.

Filters (`restalchemy.dm.filters`) are used to describe query conditions when working with storage and API filtering.

---

## Files in this section

- [Models](models.md)
  - `Model`, `ModelWithID`, `ModelWithUUID`, `ModelWithTimestamp`, and other mixins.
- [Properties](properties.md)
  - Property system: `Property`, `IDProperty`, `PropertyCollection`, `PropertyManager`, helper factories.
- [Relationships](relationships.md)
  - `relationship()`, `required_relationship()`, `readonly_relationship()`, `Relationship`, `PrefetchRelationship`.
- [Types](types.md)
  - Scalar, datetime, collection and structured types used in properties.
- [Filters](filters.md)
  - Filter clauses (`EQ`, `GT`, `In`, etc.) and logical expressions (`AND`, `OR`).

All of these files exist in four languages with the same structure:

You can find the DM reference in each language under the corresponding `reference/dm/` section.
