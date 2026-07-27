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

# SQL Sessions und Transaktionen

Modul: `restalchemy.storage.sql.sessions`

Dieses Modul definiert die Session-Klassen für PostgreSQL und MySQL, das Query-Caching sowie Helfer zur Verwaltung von Sessions.

---

## SessionQueryCache

`SessionQueryCache` ist ein Cache für Query-Ergebnisse auf Session-Ebene.

- Berechnet einen Hash aus SQL-Statement und gebundenen Werten.
- Speichert die Ergebnisse von `get_all()` und `query()`.
- Verwendet zwischengespeicherte Ergebnisse wieder, wenn dieselbe Query innerhalb derselben Session erneut ausgeführt wird.

Wird intern von `PgSQLSession` und `MySQLSession` genutzt, wenn `cache=True` gesetzt ist.

---

## PgSQLSession

`PgSQLSession` kapselt eine PostgreSQL-Verbindung samt Cursor:

- Bezieht Verbindungen über `engine.get_connection()` von der `PgSQLEngine`.
- Nutzt eine Row-Factory (`pg_rows.dict_row`), um dict-artige Zeilen zu erhalten.
- Stellt `execute()`, `execute_many()`, `commit()`, `rollback()`, `close()` bereit.
- Bietet die Helfer `batch_insert(models)` und `batch_delete(models)`:
  - Stellen sicher, dass alle Modelle vom selben Typ sind.
  - Bauen Bulk-SQL-Operationen über die Dialektklassen aus `pgsql`.

Die Session wird üblicherweise verwaltet über:

- `engine.session_manager()` aus `AbstractEngine`, oder
- den Kontextmanager `session_manager(engine, session=None)` aus diesem Modul.

---

## MySQLSession

`MySQLSession` verhält sich ähnlich wie `PgSQLSession`, verwendet aber:

- MySQL-Verbindungen von der `MySQLEngine`.
- Cursor von `mysql.connector` mit `dictionary=True`.
- Die Dialektklassen aus `mysql` (`MySQLInsert`, `MySQLBatchDelete` usw.).

Zusätzlich unterstützt sie:

- `batch_insert(models)` und `batch_delete(models)`.
- Die Übersetzung typischer Deadlock- und Integritätsfehler in Storage-Exceptions.

---

## session_manager

Für die Session-Verwaltung gibt es zwei verwandte Mechanismen:

1. `engines.AbstractEngine.session_manager()`
2. `sessions.session_manager(engine, session=None)`

`engines.AbstractEngine.session_manager()`:

- Wird am häufigsten verwendet.
- Wird keine Session übergeben, dann:
  - Erzeugt er eine neue Session über `engine.get_session()`.
  - Gibt sie an den Aufrufer weiter.
  - Committet bei Erfolg und rollt bei einer Exception zurück.
  - Schließt die Session am Ende.
- Wird eine Session übergeben, gibt er sie einfach ohne weitere Behandlung weiter.

`sessions.session_manager(engine, session=None)`:

- Verhält sich analog, ist aber im sessions-Modul implementiert.
- Kann direkt verwendet werden, wenn Sie bereits eine Engine-Instanz haben.

Beispiel:

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    # Mehrere Operationen innerhalb einer Transaktion ausführen
    foo = FooModel(foo_field1=42)
    foo.save(session=session)
```

---

## SessionThreadStorage

`SessionThreadStorage` ist ein thread-lokaler Speicher für Sessions:

- Hält genau eine Session pro Thread.
- Stellt folgende Methoden bereit:
  - `get_session()` — liefert die gespeicherte Session oder wirft `SessionNotFound`.
  - `store_session(session)` — legt eine Session für den aktuellen Thread ab und wirft `SessionConflict`, wenn bereits eine gespeichert ist.
  - `remove_session()` / `pop_session()` — löschen bzw. liefern-und-löschen die gespeicherte Session.

Engines nutzen `SessionThreadStorage` als Session-Speicher, damit:

- Eine Session einmal erzeugt und von mehreren Operationen im selben Thread wiederverwendet werden kann.
- Höherliegender Code RESTAlchemy-Sessions in eine bestehende Transaktionsverwaltung einbinden kann.
