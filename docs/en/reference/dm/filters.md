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

# Filters

Module: `restalchemy.dm.filters`

Filters describe query conditions for DM models. They are typically used by storage and API layers to build WHERE clauses and filter collections.

---

## Clause classes

All clause classes inherit from `AbstractClause`:

- Store a single `value`.
- Implement equality and string representation for debugging.

Simple comparison and membership clauses:

- `EQ(value)` — equal to.
- `NE(value)` — not equal to.
- `GT(value)` — greater than.
- `GE(value)` — greater or equal.
- `LT(value)` — less than.
- `LE(value)` — less or equal.
- `Is(value)` — `IS` comparison (e.g. `IS NULL`).
- `IsNot(value)` — `IS NOT` comparison.
- `In(value)` — membership in a collection.
- `NotIn(value)` — not in a collection.
- `Like(value)` — pattern matching.
- `NotLike(value)` — negated pattern matching.
- `ContainsAll(value)` (PostgreSQL array columns) — array `@>`, contains all given elements.
- `ContainsAny(value)` (PostgreSQL array columns) — array `&&`, overlaps with given elements.
- `JSONFields(value)` (PostgreSQL jsonb columns) — filter on keys nested inside a jsonb column; see [JSON field filters](#json-field-filters) below.

Example:

```python
from restalchemy.dm import filters

f1 = filters.EQ(10)
assert str(f1) == "10"
```

---

## Expression classes

Expressions group clauses logically.

- `AbstractExpression` — base class.
- `ClauseList` — container for multiple clauses.
- `AND(*clauses)` — logical AND over clauses or expressions.
- `OR(*clauses)` — logical OR over clauses or expressions.

These classes are not evaluated directly in Python; instead, storage and API code interpret them and translate them into SQL or other query languages.

---

## Using filters with DM + storage

Example adapted from `examples/dm_mysql_storage.py`:

```python
from restalchemy.dm import filters
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import engines, orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


# Configure engine
engines.engine_factory.configure_factory(
    db_url="mysql://test:test@127.0.0.1/test",
)


# Simple queries
print(list(FooModel.objects.get_all()))

print(FooModel.objects.get_one(filters={"foo_field1": filters.EQ(10)}))

print(list(FooModel.objects.get_all(filters={"foo_field1": filters.GT(5)})))

print(list(FooModel.objects.get_all(filters={"foo_field1": filters.In([5, 6])})))
```

Here:

- Dictionary keys are field names (`"foo_field1"`).
- Values are filter clauses (`filters.EQ(10)`, `filters.GT(5)`, `filters.In([...])`).
- Storage interprets them to build the correct SQL WHERE conditions.

---

## Complex expressions

For complex queries you can use `AND` and `OR` expressions.

Example (from `examples/dm_mysql_storage.py`):

```python
# WHERE ((`name1` = 1 AND `name2` = 2) OR (`name2` = 3))
filter_list = filters.OR(
    filters.AND({
        "name1": filters.EQ(1),
        "name2": filters.EQ(2),
    }),
    filters.AND({
        "name2": filters.EQ(3),
    }),
)

print(FooModel.objects.get_one(filters=filter_list))
```

Storage backends understand these nested expressions and produce an appropriate query.

---

## JSON field filters

`JSONFields` filters on keys nested inside a PostgreSQL `jsonb` column, and supports both equality and range clauses on those keys — not just containment:

```python
from restalchemy.dm import filters

# WHERE (spec->>'kind') = %s AND (spec->>'value')::bigint > %s
FooModel.objects.get_all(
    filters={"spec": filters.JSONFields({"kind": "foo", "value": filters.GT(10)})}
)
```

Each key in the mapping is either a plain scalar (shorthand for `EQ`) or an explicit clause (`EQ`, `NE`, `GT`, `GE`, `LT`, `LE`, `Like`, `NotLike`, `Is`, `IsNot`). Keys are combined with AND. Values are cast in the generated SQL based on their Python type (`bool` → `::boolean`, `int` → `::bigint`, `float` → `::double precision`; `str`/`None` need no cast) — this cast must be reproduced exactly in any index you build (see below), or Postgres will silently ignore the index.

### Indexing a "kind"-discriminated jsonb column

`JSONFields` is meant for the common polymorphic-JSON shape: a column always carries a discriminator key (conventionally `"kind"`), plus a handful of extra keys whose presence and meaning are private to that kind — e.g. `{"kind": "totp", "period": 30}` vs. `{"kind": "yubiotp", "device_id": "..."}` in the same column. This shape needs two kinds of index:

1. **Always index the discriminator itself** with a plain expression index — every query touching the column filters by it first, and it's the same shape for every kind:

   ```sql
   CREATE INDEX ix_t_spec_kind ON t ((spec->>'kind'));
   ```

2. **For each `(kind, field)` pair you actually query by, add a *partial* expression index scoped to that kind** — not a table-wide index on the field name, since the field's meaning (and its presence at all) is specific to one kind:

   ```sql
   CREATE INDEX ix_t_spec_totp_period ON t (((spec->>'period')::bigint))
       WHERE spec->>'kind' = 'totp';
   ```

   Measured on a 2M-row table: a query combining the discriminator with a per-kind field (`kind = 'foo' AND value > 10`) was ~2x faster with this partial index than with only the discriminator index from step 1, and a discriminator-only query against a single partial index served as an index-only scan ~9x faster than the plain discriminator index — Postgres can use a partial index's own `WHERE` clause as proof of the predicate. Filtering by several fields of the same kind together should be one composite partial index, not one index per field.

   Don't create a partial index for every `(kind, field)` combination that merely exists in the schema — each one is pure write overhead until a query actually needs it. Add them lazily, driven by real query patterns.

A GIN index (`USING gin(spec)`) does **not** speed up `JSONFields` queries: GIN accelerates `@>`/`?`/`?|`/`?&`, not the `->>` comparisons this filter compiles to, and in testing was sometimes *slower* than a plain sequential scan. It also isn't free on writes — pending-list flushes add write-latency spikes on jsonb columns updated often. Only add GIN if something else in the app genuinely queries with raw containment.

---

## Best practices

- Use simple dict-based filters (`{"field": filters.EQ(value)}`) for most cases.
- Use `AND`/`OR` expressions when you need complex logical combinations.
- Do not try to evaluate filter objects yourself; let storage or API code handle them.
- Keep filter logic close to query code (e.g. in repositories or service layer) for readability.
