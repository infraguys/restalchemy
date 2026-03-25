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

# DM + SQL storage how-to

In diesem Leitfaden wird gezeigt, wie DM-Modelle mit RESTAlchemy in einer SQL-Datenbank gespeichert werden.

Sie lernen:

- DM-Modelle mit `ModelWithUUID` und `SQLStorableMixin` zu definieren.
- Einen SQL-Engine (MySQL oder PostgreSQL) zu konfigurieren.
- CRUD-Operationen mit `.save()`, `.delete()` und `Model.objects` auszuführen.
- Filter für Abfragen zu verwenden.

Die Beispiele basieren auf `examples/dm_mysql_storage.py` und `examples/dm_pg_storage.py`.

---

## Voraussetzungen

- RESTAlchemy ist installiert (siehe `installation.md`).
- Eine laufende Datenbank:
  - MySQL/MariaDB oder
  - PostgreSQL.
- Passender Python-Treiber, z.B.:
  - `mysql-connector-python` für MySQL.
  - `psycopg[binary]` für PostgreSQL.
- Tabellen wurden entsprechend den Modell-Definitionen angelegt (siehe Migrationen).

---

## 1. DM-Modelle für SQL definieren

Muster für ein SQL-gestütztes Modell:

- Von `models.ModelWithUUID` (oder `ModelWithID`) erben.
- Zusätzlich von `orm.SQLStorableMixin` erben.
- `__tablename__` setzen.
- Felder mit DM-Properties und Types definieren.

Beispiel (vereinfacht aus `dm_mysql_storage.py`):

```python
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "bars"
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

---

## 2. SQL-Engine konfigurieren

Nutzen Sie `restalchemy.storage.sql.engines.engine_factory`, um eine Engine zu erstellen.

### MySQL-Beispiel

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/test",
)
```

### PostgreSQL-Beispiel

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="postgresql://postgres:password@127.0.0.1:5432/ra_tests",
)
```

`configure_factory()` sollte einmal beim Start des Programms aufgerufen werden. Danach beziehen alle `SQLStorableMixin`-Modelle die Engine über `engine_factory.get_engine()`.

Optionale Parameter:

- `config` — Engine-spezifische Einstellungen (Poolgrößen, Timeouts usw.).
- `query_cache` — aktiviert Query-Caching auf Session-Ebene.

---

## 3. Tabellen und Migrationen

RESTAlchemy legt Tabellen nicht automatisch an; dazu dient das Migrationssystem.

Wichtige Befehle (siehe `README.rst`):

- `ra-new-migration` — neue Migrationsdateien erzeugen.
- `ra-apply-migration` — Migrationen anwenden.

In den Beispielen finden Sie kommentierte SQL-DDLs, z.B. in `dm_mysql_storage.py`.

---

## 4. CRUD-Operationen

### Erstellen und speichern

```python
foo1 = FooModel(foo_field1=10)
foo1.save()  # INSERT in foos

bar1 = BarModel(bar_field1="test", foo=foo1)
bar1.save()  # INSERT in bars
```

### Daten lesen

```python
# Alle Bars
all_bars = list(BarModel.objects.get_all())

# Ein Bar per Primärschlüssel
same_bar = BarModel.objects.get_one(filters={"uuid": bar1.get_id()})

# Alle Bars für ein bestimmtes FooModel
bars_for_foo = list(BarModel.objects.get_all(filters={"foo": foo1}))

# Als Dictionary
print(bar1.as_plain_dict())
```

### Aktualisieren

```python
foo2 = FooModel(foo_field1=11, foo_field2="some text")
foo2.save()

foo2.foo_field2 = "updated text"
foo2.save()  # UPDATE
```

### Löschen

```python
for foo in FooModel.objects.get_all():
    foo.delete()
```

---

## 5. Filter

Filter kommen aus `restalchemy.dm.filters` und werden an `get_all()` / `get_one()` übergeben.

### Einfache Filter

```python
from restalchemy.dm import filters

one = FooModel.objects.get_one(filters={"foo_field1": filters.EQ(10)})

greater = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.GT(5)})
)

subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.In([5, 6])})
)

not_subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.NotIn([1, 2])})
)
```

### Komplexe Ausdrücke

```python
from restalchemy.dm import filters

filter_expr = filters.OR(
    filters.AND({
        "foo_field1": filters.EQ(1),
        "foo_field2": filters.EQ("2"),
    }),
    filters.AND({"foo_field2": filters.EQ("3")}),
)

foo = FooModel.objects.get_one(filters=filter_expr)
```

---

## 6. Transaktionen und Sessions

Standardmäßig verwendet jede Operation eine eigene Session und Transaktion.

Für zusammenhängende Operationen in einer Transaktion können Sie `engine.session_manager()` verwenden.

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    foo = FooModel(foo_field1=42)
    foo.save(session=session)

    bar = BarModel(bar_field1="x", foo=foo)
    bar.save(session=session)
```

Alle Operationen im `with`-Block laufen in einer Transaktion.

---

## Zusammenfassung

- DM-Modelle: `ModelWithUUID` + `SQLStorableMixin` + `__tablename__`.
- Engine-Konfiguration: `engine_factory.configure_factory()`.
- Tabellen/Migrationen: über `ra-*`-Befehle.
- CRUD: `.save()`, `.delete()`, `Model.objects.get_all()/get_one()`.
- Filter: `restalchemy.dm.filters`.
- Transaktionen: bei Bedarf über explizite Sessions.
