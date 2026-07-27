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

# SQL Engines

Modul: `restalchemy.storage.sql.engines`

Dieses Modul enthält die Engine-Factory und konkrete Engines für MySQL und PostgreSQL.

---

## AbstractEngine

`AbstractEngine` definiert das gemeinsame Verhalten aller SQL-Engines:

- Parst die Datenbank-URL.
- Stellt Datenbankname, Host, Port, Benutzername und Passwort bereit.
- Hält den SQL-Dialekt (`mysql.MySQLDialect` oder `pgsql.PgSQLDialect`).
- Bietet `session_manager()` als Kontextmanager.

Wichtige Properties und Methoden:

- `URL_SCHEMA` (abstrakt): erwartetes URL-Schema, z. B. `"mysql"`, `"postgresql"`.
- `DEFAULT_PORT` (abstrakt): Port, der verwendet wird, wenn die URL keinen angibt.
- `db_name`, `db_username`, `db_password`, `db_host`, `db_port`.
- `dialect`: das Dialekt-Objekt.
- `query_cache`: ob der Query-Cache auf Session-Ebene aktiv ist.
- `get_connection()`: liefert eine Verbindung (in Unterklassen implementiert).
- `get_session()`: liefert ein Session-Objekt (in Unterklassen implementiert).
- `session_manager(session=None)`: Kontextmanager, der Commit/Rollback und das Schließen der Session übernimmt.
- `get_session_storage()`: liefert den Session-Speicher (`SessionThreadStorage`).

Beispiel:

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()
print(engine.db_name)
```

---

## PostgreSQL-Engine

### `PgSQLEngine`

- `URL_SCHEMA = "postgresql"`.
- `DEFAULT_PORT` stammt aus `restalchemy.common.constants.RA_POSTGRESQL_DB_PORT`.
- Nutzt `psycopg_pool.ConnectionPool` für Verbindungen.
- Dialekt: `pgsql.PgSQLDialect()`.
- Session-Typ: `sessions.PgSQLSession`.

Konstruktor:

```python
PgSQLEngine(db_url, config=None, query_cache=False)
```

- `db_url`: PostgreSQL-Verbindungs-URL.
- `config`: wird an `psycopg_pool.ConnectionPool` durchgereicht.
- `query_cache`: aktiviert das Query-Caching.

Methoden:

- `get_session()`: liefert `PgSQLSession(engine=self)`.
- `get_connection()`: holt eine Verbindung aus dem Pool.
- `close_connection(conn)`: gibt die Verbindung an den Pool zurück.

Die Engine wird intern von `EngineFactory` erzeugt.

---

## MySQL-Engine

### `MySQLEngine`

- `URL_SCHEMA = "mysql"`.
- `DEFAULT_PORT` stammt aus `RA_MYSQL_DB_PORT`.
- Nutzt `mysql.connector.pooling.MySQLConnectionPool`.
- Dialekt: `mysql.MySQLDialect()`.
- Session-Typ: `sessions.MySQLSession`.

Konstruktor:

```python
MySQLEngine(db_url, config=None, query_cache=False)
```

- `db_url`: MySQL-Verbindungs-URL.
- `config`: Pool-Konfiguration.
- `query_cache`: aktiviert das Query-Caching.

Methoden:

- `get_connection()`: liefert eine Verbindung aus dem Pool.
- `get_session()`: liefert `MySQLSession(engine=self)`.

---

## EngineFactory und engine_factory

### `EngineFactory`

Ein Singleton, das Engine-Instanzen konfiguriert und vorhält.

Wichtige Methoden:

- `configure_factory(db_url, config=None, query_cache=False, name="default")`
  - Erzeugt anhand von `db_url` eine Engine-Instanz und legt sie unter `name` ab.
  - Leitet die Engine-Klasse aus dem URL-Schema ab ("mysql", "postgresql").
- `configure_postgresql_factory(conf, section, name)`
  - Hilfsmethode, um PostgreSQL aus einem Config-Objekt zu konfigurieren.
- `configure_mysql_factory(conf, section, name)`
  - Hilfsmethode, um MySQL aus einem Config-Objekt zu konfigurieren.
- `get_engine(name="default")`
  - Liefert die konfigurierte Engine-Instanz.
- `destroy_engine(name="default")` / `destroy_all_engines()`
  - Entfernen Engines aus der Factory.

Auf Modulebene:

```python
engine_factory = EngineFactory()
```

Die meisten Anwendungen verwenden dieses Singleton:

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(db_url="mysql://...")
engine = engines.engine_factory.get_engine()
```

---

## DBConnectionUrl

`DBConnectionUrl` ist ein kleiner Helfer, der eine DB-URL parst und eine zensierte String-Darstellung liefert.

- Speichert die geparste URL.
- Die Property `url` liefert den vollständigen URL-String.
- `__repr__` verbirgt das Passwort und ersetzt es durch `:<censored>@`.

Das ist vor allem für Logging und Debugging nützlich.
