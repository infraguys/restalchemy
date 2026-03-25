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

## Best practices

- Use simple dict-based filters (`{"field": filters.EQ(value)}`) for most cases.
- Use `AND`/`OR` expressions when you need complex logical combinations.
- Do not try to evaluate filter objects yourself; let storage or API code handle them.
- Keep filter logic close to query code (e.g. in repositories or service layer) for readability.
