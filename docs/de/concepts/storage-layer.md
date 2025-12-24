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

# Storage layer

Die Storage-Schicht in RESTAlchemy ist für das Persistieren von DM-Modellen und deren Wiederherstellung zuständig.

Sie bildet eine eigene Schicht zwischen Data Model (DM) und API.

---

## Modulüberblick

Wichtige Module für SQL-Storage:

- `restalchemy.storage.base`
  - Abstrakte Interfaces für speicherbare Modelle und Collections.
- `restalchemy.storage.exceptions`
  - Storage-spezifische Exceptions.
- `restalchemy.storage.sql.engines`
  - Engine-Factory und Implementierungen für MySQL/PostgreSQL.
- `restalchemy.storage.sql.sessions`
  - Datenbank-Sessions, Transaktionen, Session-Query-Cache.
- `restalchemy.storage.sql.orm`
  - ORM-ähnliche Mixins und Collections (`SQLStorableMixin`, `ObjectCollection`).
- `restalchemy.storage.sql.tables`
  - Tabellenabstraktion für ORM und Dialekte.
- `restalchemy.storage.sql.dialect.*`
  - Dialekt-spezifische Query-Builder für MySQL und PostgreSQL.

Im Normalfall arbeiten Sie nur mit:

- DM-Modellen + `orm.SQLStorableMixin`;
- `engines.engine_factory.configure_factory()` zur Konfiguration des Engines;
- `Model.objects` und den Methoden `save()` / `delete()`.

---

## Architekturüberblick

### 1. DM-Modell

Sie definieren ein Modell, das von:

- `models.ModelWithUUID` (oder einer anderen `Model*`-Basisklasse) und
- `orm.SQLStorableMixin`

erbt.

Beispiel (vereinfacht aus `examples/dm_mysql_storage.py`):

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

### 2. Engine und Sessions

`restalchemy.storage.sql.engines` enthält eine `engine_factory`, die SQL-Engines verwaltet.

Typische Konfiguration:

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/mydb",
)
```

Kernideen:

- **Engine** parst `db_url`, konfiguriert Connection-Pool und Dialekt.
- **Session** (`PgSQLSession` / `MySQLSession`) führt Statements aus.
- `session_manager(engine, session=None)` (in `sessions.py`) kapselt Workflows in Transaktionen.

### 3. ORM-Mixins und Collections

`restalchemy.storage.sql.orm` stellt bereit:

- `SQLStorableMixin` — Mixin für DM-Modelle, die in SQL gespeichert werden.
- `ObjectCollection` — Collection-API, erreichbar über `Model.objects`.

Verantwortlichkeiten:

- **`SQLStorableMixin`**:
  - Verknüpft DM-Modell und Tabelle über `__tablename__` und `get_table()`.
  - Implementiert `insert()`, `save()`, `update()`, `delete()`.
  - Konvertiert DM-Properties in speicherbare Werte und zurück.

- **`ObjectCollection`**:
  - Methoden `get_all()`, `get_one()`, `get_one_or_none()`, `query()`, `count()`.
  - Nutzt `restalchemy.dm.filters` zur Beschreibung von WHERE-Bedingungen.

### 4. Dialekte und Tabellen

Dialekt-Module (`restalchemy.storage.sql.dialect.*`) und `tables.SQLTable`:

- Erzeugen SQL-Statements (SELECT/INSERT/UPDATE/DELETE).
- Binden Parameter.
- Führen Queries über Sessions aus.

Diese Komponenten sind intern; Sie müssen sie selten direkt verwenden.

---

## Lebenszyklus eines SQL-gestützten Modells

1. **Modell definieren**
   - Von `ModelWithUUID` und `SQLStorableMixin` erben.
   - `__tablename__` festlegen.
   - Felder und Beziehungen über DM-Properties definieren.

2. **Engine konfigurieren**
   - Einmalig beim Start: `engine_factory.configure_factory(db_url=...)`.

3. **Tabellen/Migrationen**
   - Mit `ra-new-migration` und `ra-apply-migration` Datenbank-Schema anlegen/ändern.

4. **CRUD-Operationen**
   - Instanzen erzeugen und `.save()` aufrufen.
   - Über `Model.objects.get_all()` / `.get_one(filters=...)` lesen.
   - `.delete()` zum Löschen verwenden.

5. **Filter und komplexe Queries**
   - Filter mit `restalchemy.dm.filters` aufbauen und an `objects.get_all()` / `get_one()` übergeben.

6. **Transaktionen und Sessions (optional)**
   - Für feingranulare Kontrolle `session_manager()` explizit verwenden.

Alle Schritte werden ausführlich im DM+SQL How-to und in `examples/dm_mysql_storage.py` sowie `examples/dm_pg_storage.py` gezeigt.
