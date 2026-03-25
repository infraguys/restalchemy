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

# Types

Module: `restalchemy.dm.types`

DM types describe the allowed values for properties and how values are converted to/from simple representations (for JSON, OpenAPI, storage, etc.).

All property types inherit from `BaseType`.

---

## BaseType

### `BaseType`

Core interface for all DM types:

- `validate(value) -> bool`: checks whether the value is acceptable.
- `to_simple_type(value)`: converts a value to a simple Python type (string, number, dict, list…).
- `from_simple_type(value)`: converts back from a simple type.
- `from_unicode(value)`: parses a string representation.
- `to_openapi_spec(prop_kwargs)`: builds OpenAPI schema fragment.

Many concrete types are based on `BasePythonType`, which wraps a Python type like `int` or `str`.

---

## Scalar types

### `Boolean`

- Wraps `bool`.
- Accepts any truthy/falsy value from `from_simple_type()` and string representations from `from_unicode()`.

### `String`

- Wraps `str` with length constraints.
- Parameters: `min_length`, `max_length`.
- `to_openapi_spec()` adds `minLength`/`maxLength`.

Common subclasses:

- `Email` — validates email addresses (with optional deliverability checks).

### `Integer`

- Wraps `int` with `min_value` and `max_value`.
- `Int8`, `Int16`, etc. are specialized variants.

### `Float`

- Wraps `float` with bounds.

### `Decimal`

- Wraps `decimal.Decimal` with optional `max_decimal_places`.
- Serializes to/from string to avoid precision loss.

### `UUID`

- Wraps `uuid.UUID`.
- Serializes to string form.

### `Enum`

- Restricts values to a given set of allowed values.

Example:

```python
from restalchemy.dm import types

status_type = types.Enum(["pending", "active", "disabled"])
```

Use it in properties:

```python
status = properties.property(status_type, default="pending")
```

---

## Datetime and time-related types

### `UTCDateTime` (deprecated) and `UTCDateTimeZ`

- Both wrap `datetime.datetime`.
- `UTCDateTimeZ` enforces `tzinfo == datetime.timezone.utc` and is recommended.
- Serialize to string in MySQL / RFC3339-like format.

### `TimeDelta`

- Wraps `datetime.timedelta`.
- Serializes to seconds as float.

### `DateTime`

- Legacy timestamp type, serializes to Unix timestamps.

---

## Collection types

### `List` and `TypedList`

- `List` validates that the value is a Python list.
- `TypedList(nested_type)` ensures each element is valid for `nested_type`.

Example:

```python
from restalchemy.dm import types


tags_type = types.TypedList(types.String(max_length=32))
```

### `Dict` and structured dicts

- `Dict` validates that the value is a `dict` with string keys.
- `TypedDict(nested_type)` enforces that all values match `nested_type`.

Schema-based dicts:

- `SoftSchemeDict(scheme)` — dict with keys that are a subset of the scheme.
- `SchemeDict(scheme)` — dict that must match the scheme exactly.

Example:

```python
from restalchemy.dm import types


settings_scheme = {
    "retries": types.Integer(min_value=0),
    "timeout": types.Float(min_value=0.0),
}

settings_type = types.SoftSchemeDict(settings_scheme)
```

Use it in a property:

```python
settings = properties.property(settings_type, default=dict)
```

---

## Nullable and wrapper types

### `AllowNone(nested_type)`

- Allows either `None` or a valid value for `nested_type`.
- `to_simple_type()` and `from_simple_type()` propagate through `nested_type` when not `None`.
- `to_openapi_spec()` adds `nullable: true`.

Example:

```python
maybe_uuid = types.AllowNone(types.UUID())

uuid_or_none = properties.property(maybe_uuid)
```

---

## Regexp and URL-related types

### `BaseRegExpType` and `BaseCompiledRegExpTypeFromAttr`

Low-level base classes for regexp-based types.

Concrete types include:

- `Uri` — validates URI paths ending with a UUID.
- `Mac` — validates MAC addresses.
- `Hostname` (deprecated) — see `types_network`.
- `Url` — HTTP/FTP URL validator.

These types are useful for networking and resource identifiers.

---

## Dynamic and network types

Additional specialized types live in:

- `restalchemy.dm.types_dynamic`
- `restalchemy.dm.types_network`

Examples include:

- More advanced hostnames, IP networks, CIDR ranges.
- Dynamic structures with runtime-defined schemas.

This reference does not list all of them exhaustively, but the basic usage pattern is always the same:

1. Instantiate the type.
2. Use it in `properties.property()`.
3. Let DM validation and conversion handle the rest.

---

## Best practices

- Prefer DM types (`types.String`, `types.Integer`, etc.) to raw Python types; they encode validation and OpenAPI metadata.
- Use `AllowNone` instead of manually allowing `None` in your business logic.
- Use `Enum` for small closed sets of allowed values.
- For complex JSON-like structures, use `SoftSchemeDict`, `SchemeDict` or `TypedDict` instead of a bare `Dict`.
