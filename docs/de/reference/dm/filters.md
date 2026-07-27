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

Alle Klauselklassen erben von `AbstractClause`:

- Sie speichern einen einzelnen `value`.
- Sie implementieren Gleichheit und eine String-Darstellung zum Debuggen.

Einfache Vergleichs- und Membership-Klauseln:

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
- `ContainsAll(value)` (PostgreSQL-Array-Spalten) — Array-Operator `@>`, enthält alle angegebenen Elemente.
- `ContainsAny(value)` (PostgreSQL-Array-Spalten) — Array-Operator `&&`, überschneidet sich mit den angegebenen Elementen.
- `JSONFields(value)` (PostgreSQL-jsonb-Spalten) — filtert auf Keys innerhalb einer jsonb-Spalte; siehe [Filter auf JSON-Felder](#json-field-filters) weiter unten.

Beispiel:

```python
from restalchemy.dm import filters

f1 = filters.EQ(10)
assert str(f1) == "10"
```

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

Dabei gilt:

- Die Dict-Keys sind Feldnamen (`"foo_field1"`).
- Die Werte sind Filterklauseln (`filters.EQ(10)`, `filters.GT(5)`, `filters.In([...])`).
- Die Storage-Schicht interpretiert sie und baut daraus die passenden SQL-WHERE-Bedingungen.

---

## Komplexe Ausdrücke

Für komplexe Abfragen können Sie `AND`- und `OR`-Ausdrücke verwenden.

Beispiel (aus `examples/dm_mysql_storage.py`):

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

Die Storage-Backends verstehen solche verschachtelten Ausdrücke und erzeugen daraus eine passende Query.

---

## Filter auf JSON-Felder {#json-field-filters}

`JSONFields` filtert auf Keys innerhalb einer PostgreSQL-`jsonb`-Spalte und unterstützt für diese Keys nicht nur Containment, sondern auch Gleichheits- und Bereichsklauseln:

```python
from restalchemy.dm import filters

# WHERE (spec->>'kind') = %s AND (spec->>'value')::bigint > %s
FooModel.objects.get_all(
    filters={"spec": filters.JSONFields({"kind": "foo", "value": filters.GT(10)})}
)
```

Jeder Key im Mapping ist entweder ein einfacher Skalar (Kurzform für `EQ`) oder eine explizite Klausel (`EQ`, `NE`, `GT`, `GE`, `LT`, `LE`, `Like`, `NotLike`, `Is`, `IsNot`). Die Keys werden mit AND verknüpft. Die Werte werden im generierten SQL anhand ihres Python-Typs gecastet (`bool` → `::boolean`, `int` → `::bigint`, `float` → `::double precision`; `str`/`None` brauchen keinen Cast) — dieser Cast muss in jedem Index, den Sie anlegen, exakt reproduziert werden (siehe unten), sonst ignoriert Postgres den Index stillschweigend.

### Indizierung einer per "kind" diskriminierten jsonb-Spalte

`JSONFields` ist für die übliche Form von polymorphem JSON gedacht: Die Spalte enthält immer einen Diskriminator-Key (konventionell `"kind"`) sowie eine Handvoll weiterer Keys, deren Vorhandensein und Bedeutung nur für diesen kind gelten — z. B. `{"kind": "totp", "period": 30}` und `{"kind": "yubiotp", "device_id": "..."}` in derselben Spalte. Diese Form braucht zwei Arten von Indizes:

1. **Indizieren Sie immer den Diskriminator selbst** mit einem einfachen Expression-Index: Jede Query auf die Spalte filtert zuerst danach, und die Form ist für jeden kind dieselbe:

   ```sql
   CREATE INDEX ix_t_spec_kind ON t ((spec->>'kind'));
   ```

2. **Für jedes `(kind, field)`-Paar, nach dem Sie tatsächlich abfragen, legen Sie einen auf diesen kind eingeschränkten *partiellen* Expression-Index an** — keinen tabellenweiten Index auf den Feldnamen, denn die Bedeutung des Feldes (und ob es überhaupt existiert) ist spezifisch für einen kind:

   ```sql
   CREATE INDEX ix_t_spec_totp_period ON t (((spec->>'period')::bigint))
       WHERE spec->>'kind' = 'totp';
   ```

   Gemessen an einer Tabelle mit 2 Mio. Zeilen: Eine Query, die den Diskriminator mit einem kind-spezifischen Feld kombiniert (`kind = 'foo' AND value > 10`), war mit diesem partiellen Index rund doppelt so schnell wie nur mit dem Diskriminator-Index aus Schritt 1; eine Query allein auf den Diskriminator gegen einen einzelnen partiellen Index lief als Index-Only-Scan etwa 9-mal schneller als über den einfachen Diskriminator-Index — Postgres kann die `WHERE`-Klausel eines partiellen Index als Beweis für das Prädikat nutzen. Wird nach mehreren Feldern desselben kind gemeinsam gefiltert, gehört das in einen zusammengesetzten partiellen Index und nicht in einen Index je Feld.

   Legen Sie nicht für jede `(kind, field)`-Kombination einen partiellen Index an, die im Schema bloß vorkommt: Solange keine Query sie wirklich braucht, ist das reiner Schreib-Overhead. Fügen Sie sie bedarfsgetrieben hinzu, orientiert an echten Abfragemustern.

Ein GIN-Index (`USING gin(spec)`) beschleunigt `JSONFields`-Queries **nicht**: GIN hilft bei `@>`/`?`/`?|`/`?&`, nicht bei den `->>`-Vergleichen, zu denen dieser Filter kompiliert, und war in Tests teilweise *langsamer* als ein einfacher Sequential Scan. Er ist auch beim Schreiben nicht kostenlos — das Leeren der Pending-List erzeugt Latenzspitzen bei häufig aktualisierten jsonb-Spalten. Legen Sie GIN nur an, wenn etwas anderes in der Anwendung tatsächlich mit reinem Containment abfragt.

---

## Best Practices

- Für einfache Fälle reichen Dict-basierte Filter: `{ "field": filters.EQ(value) }`.
- Nutzen Sie `AND`/`OR` für komplexe logische Kombinationen.
- Überlassen Sie die Auswertung von Filtern immer der Storage- oder API-Schicht.
- Halten Sie die Filterlogik nahe am Query-Code (z. B. in Repositories oder in der Service-Schicht), das verbessert die Lesbarkeit.
