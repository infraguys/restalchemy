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
