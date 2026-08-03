<!--
Copyright 2026 Genesis Corporation

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

# Filtering collections over HTTP

This guide covers the query parameters a collection endpoint (the `FILTER`
method) understands, and how they become
[DM filters](../reference/dm/filters.md).

Filtering is enabled per resource:

```python
class TaggedController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        TaggedModel,
        process_filters=True,
    )
```

Without `process_filters=True` the parameters are passed through as raw
strings and are not parsed or validated at all.

---

## Scalar fields

A parameter named after a field filters by equality; the value is parsed
into the field's type, so a value the type rejects is a `400`, not a
comparison that silently matches nothing:

```http
GET /v1/vms/?name=web-1          ->  EQ("web-1")
GET /v1/vms/?name=web-1&name=web-2  ->  In(["web-1", "web-2"])
```

Repeating a parameter therefore reads as "any of these".

---

## Array fields

An array field (`ModelWithTags` and its `tags` are the common case) behaves
differently, and the difference is easy to trip over:

```http
GET /v1/tagged/?tags=env:prod
```

means `tags = ARRAY['env:prod']` — the whole array equals that one element.
It is a valid filter, but it is not a search: a row tagged
`['env:prod', 'region:eu']` does not match.

Searching by element is what the filter expression below is for —
`?q=tags:"env:prod"` — and there is no field parameter that does it. The
reason is the values: a tag reads `owner:user:<uuid>`, punctuation and
all, and a parameter whose value carries its own delimiters cannot also
carry an operator. An expression can, because it has quoting.

---

## Filter expressions

The parameters above are an AND of equalities and nothing else. Where that
is not enough — OR, grouping, negation, ranges — a collection endpoint
also takes an expression, in a subset of
[AIP-160](https://google.aip.dev/160), under a single parameter:

```http
GET /v1/vms/?q=name = "web-1" AND size > 10
GET /v1/vms/?q=tags:"env:prod" OR tags:"env:staging"
GET /v1/vms/?q=NOT (state = error) AND created_at >= "2026-07-01T00:00:00Z"
```

The parameter is `q` by default. Wherever the language is on, the name is
taken out of the field namespace, so a resource that has a field called
`q` renames it — or switches the language off, and the parameter goes back
to whatever it meant before:

```python
class VmController(controllers.BaseResourceController):
    __filter_param__ = "filter"   # or None to switch the language off
```

### Operators

| Written | Becomes | |
|---|---|---|
| `name = "web-1"` | `EQ` | |
| `name != "web-1"` | `NE` | |
| `size > 10`, `>=`, `<`, `<=` | `GT`, `GE`, `LT`, `LE` | |
| `name = null` | `Is(None)` | `!= null` gives `IsNot(None)` |
| `tags:"env:prod"` | `ContainsAll` | an array holds the element |
| `description:*` | `IsNot(None)` | the field is set |
| `spec.kind = "totp"` | `JSONFields` | one key inside a `jsonb` column |
| `AND` `OR` `NOT` `(...)` | `AND` `OR` `NOT` | the keywords are uppercase |

Two things regularly surprise people, both inherited from AIP-160.

`OR` binds **tighter** than `AND`: `a = 1 OR b = 2 AND c = 3` reads as
`(a = 1 OR b = 2) AND c = 3`. Parenthesise when in doubt.

Whitespace between two restrictions is an implicit `AND`, so
`name = web-1 size > 10` is a conjunction.

### Quoting

A value carrying `:`, `.` or a space has to be quoted, or its punctuation
reads as more syntax:

```http
?q=tags:"env:prod"                       # right
?q=tags:env:prod                         # 400 — the second : is an operator
?q=created_at >= "2026-07-01T00:00:00Z"
```

Unquoted, `null`, `true`, `false` and `*` are literals of the language;
quoted, they are those strings.

### Both, or either

No operator spells `ContainsAny`, and none needs to. `tags:"a"` is
`tags @> ARRAY['a']`, so the boolean operators already say it:

```http
?q=tags:"env:prod" AND tags:"region:eu"    ->  tags @> ARRAY[...]   both
?q=tags:"env:prod" OR tags:"env:staging"   ->  tags && ARRAY[...]   either
```

Clauses on one field are merged into a single array operator, so either
form is one index probe rather than one per element. `name = a OR name = b`
merges the same way, into `name = ANY(...)`.

Merging never changes what an expression asks for. `@>` over several
elements is not the union of them, so a containment already widened by an
`AND` keeps its own operator when it is then `OR`ed:

```http
?q=(tags:"a" AND tags:"b") OR tags:"c"   ->  tags @> ARRAY['a','b'] OR tags @> ARRAY['c']
```

That merging is why the query-parameter form needs two operator names and
the expression needs none: a list of parameters has no AND and no OR to
carry the difference.

### Together with the field parameters

The two combine with AND, so they mix freely:

```http
GET /v1/vms/?state=active&q=tags:"env:prod" OR tags:"env:staging"
```

### What an expression is refused for

Each of these is a `400`, never a filter that quietly does something else:

- a field the resource does not have, or a value its type rejects;
- a field the resource hides from responses — via `hidden_fields`, or
  `Permissions.HIDDEN` for the `FILTER` method. Comparing against a
  field the API never returns would hand it back a bit at a time, so a
  hidden field answers exactly as an unknown one does. The same rule
  covers a field parameter (`?secret=x`) and `sort_key`, which orders
  the collection by a value it never shows;
- an expression naming a custom property (see below);
- an operator the storage dialect cannot compile — `:` and `spec.kind`
  are PostgreSQL only;
- more than one `q` in one request: whether the two should be ANDed or
  ORed is not in the request;
- an expression over 100 nodes, nested deeper than 8, or longer than 4096
  characters — the caps are `__filter_max_nodes__`, `__filter_max_depth__`
  and `__filter_max_length__` on the controller, and they are there
  because a filter string is untrusted input. The length is checked first:
  the other two are counted while parsing, and parsing starts by scanning
  the whole string.

Left out deliberately: functions (`f(x)`), a bare literal as a fuzzy
search across fields, `-` as a synonym for `NOT`, wildcards in `=`,
field-to-field comparison, and traversal deeper than one key.

---

## Indexing

An array filter is only as good as its index. Declare a GIN index in the
migration that creates the table:

```sql
CREATE INDEX idx_tagged_tags ON tagged USING GIN (tags);
```

For a selective value — a tag carried by a small share of the rows, which
is what an owner or identity tag looks like — the planner answers from the
index. For a value nearly every row carries, it walks the primary key and
applies the tag as a filter instead; that is the cheaper plan under a
`LIMIT`, not a missing index.

---

## Filtering with pagination

Pagination composes with filters: the cursor's boundary is ANDed onto
whatever the caller filtered by, so the two travel together.

```http
GET /v1/tagged/?project_id=<uuid>&page_limit=50
```

The selective case stays on the GIN index with the cursor applied as an
ordinary filter over the rows it returns.

An expression paginates the same way — the cursor is built from the field
parameters and the expression is ANDed on straight after:

```http
GET /v1/tagged/?q=tags:"env:prod"&page_limit=50&page_marker=<uuid>
```

Send the same expression with every page. A cursor only means anything
against the filter it was issued under; changing the filter mid-walk skips
or repeats rows. Keep in mind too that keyset pagination leans on the index
behind `ORDER BY`, and an `OR` across several fields can take the planner
off it — narrow with field parameters where you can.

---

## Custom properties

Filters on custom (non-storage) properties are applied in Python after the
query, and only `EQ` and `In` are supported there — anything else, an array
operator included, is a `400`.

The expression parameter does not reach them at all. They are filtered over
the rows the query already returned, and an expression cannot be split into
a storage half and a Python half: there is nowhere to evaluate
`stored = 1 OR custom = 2`. Naming one in `q` is a `400`; `?custom=2` still
works.

---

## See also

- [Filters reference](../reference/dm/filters.md) — the clause classes
  themselves, including `JSONFields` for `jsonb` columns.
- [Models reference](../reference/dm/models.md) — `ModelWithTags`.
- [Basic CRUD](api-basic-crud.md) — where `process_filters` comes from.
