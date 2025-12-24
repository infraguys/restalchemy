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

# Storage Referenz

Dieser Abschnitt beschreibt die Storage-Schicht in RESTAlchemy.

Der meiste benutzernahe Code liegt in `restalchemy.storage.sql.*` und wird zusammen mit DM-Modellen und der API-Schicht verwendet.

---

## Module

- `restalchemy.storage.base`
  - Abstrakte Interfaces für speicherbare Modelle und Collections.
- `restalchemy.storage.exceptions`
  - Exceptions der Storage-Schicht.
- `restalchemy.storage.sql.engines`
  - SQL-Engines und Factory für MySQL/PostgreSQL.
- `restalchemy.storage.sql.sessions`
  - Sessions, Transaktionshelfer und Query-Cache.
- `restalchemy.storage.sql.orm`
  - ORM-ähnliche Mixins und `ObjectCollection`.
- `restalchemy.storage.sql.tables`
  - Tabellenabstraktion.
- `restalchemy.storage.sql.dialect.*`
  - Dialekt-spezifische Query-Builder.

---

## Typische Einstiegspunkte

1. Engine konfigurieren:

   ```python
   from restalchemy.storage.sql import engines

   engines.engine_factory.configure_factory(
       db_url="mysql://user:password@127.0.0.1:3306/test",
   )
   ```

2. DM-Modelle definieren, die `orm.SQLStorableMixin` verwenden, und `__tablename__` setzen.

3. Verwenden:

   - `Model.objects.get_all()` / `Model.objects.get_one()` zum Lesen.
   - `.save()` und `.delete()` auf Modellinstanzen zum Schreiben.

Weitere Details:

- [SQL Engines](sql-engines.md)
- [SQL ORM-Mixins und Collections](sql-orm.md)
- [SQL Sessions und Transaktionen](sql-sessions.md)
