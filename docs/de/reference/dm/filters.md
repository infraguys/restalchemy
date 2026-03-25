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

Modul: `restalchemy.dm.filters`

Filters beschreiben Abfragebedingungen für DM-Modelle. Sie werden von Storage- und API-Schichten interpretiert.

---

## Klausel-Klassen

Alle Klauseln erben von `AbstractClause` und kapseln einen Wert.

Vergleichs- und Membership-Klauseln:

- `EQ(value)` — gleich.
- `NE(value)` — ungleich.
- `GT(value)` — größer.
- `GE(value)` — größer oder gleich.
- `LT(value)` — kleiner.
- `LE(value)` — kleiner oder gleich.
- `Is(value)` — `IS` Vergleich (z.B. `IS NULL`).
- `IsNot(value)` — `IS NOT`.
- `In(value)` — Mitgliedschaft in einer Menge.
- `NotIn(value)` — nicht in einer Menge.
- `Like(value)` — Pattern-Matching.
- `NotLike(value)` — negiertes Pattern-Matching.

---

## Ausdrucksklassen

- `AbstractExpression` — Basis.
- `ClauseList` — Liste von Klauseln.
- `AND(*clauses)` — logisches UND.
- `OR(*clauses)` — logisches ODER.

Die Ausdrücke werden nicht direkt ausgewertet, sondern z.B. in SQL übersetzt.

---

## Verwendung mit DM + SQL Storage

Beispiel (vereinfacht aus `examples/dm_mysql_storage.py`):

```python
from restalchemy.dm import filters
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import engines, orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


engines.engine_factory.configure_factory(
    db_url="mysql://test:test@127.0.0.1/test",
)

print(list(FooModel.objects.get_all()))
print(FooModel.objects.get_one(filters={"foo_field1": filters.EQ(10)}))
print(list(FooModel.objects.get_all(filters={"foo_field1": filters.GT(5)})))
print(list(FooModel.objects.get_all(filters={"foo_field1": filters.In([5, 6])})))
```

---

## Komplexe Ausdrücke

```python
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

---

## Best Practices

- Für einfache Fälle reichen Dict-basierte Filter: `{ "field": filters.EQ(value) }`.
- Nutzen Sie `AND`/`OR` für komplexe logische Kombinationen.
- Überlassen Sie die Auswertung von Filtern immer der Storage- oder API-Schicht.
