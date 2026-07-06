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

`AbstractEngine` definiert gemeinsames Verhalten für Engines:

- Parst die DB-URL.
- Stellt `db_name`, `db_host`, `db_port`, `db_username`, `db_password` bereit.
- Hält den SQL-Dialekt.
- Bietet `session_manager()` als Kontextmanager.

---

## PgSQLEngine

- `URL_SCHEMA = "postgresql"`.
- Nutzt `psycopg_pool.ConnectionPool`.
- Dialekt: `pgsql.PgSQLDialect()`.
- Session: `sessions.PgSQLSession`.

---

## MySQLEngine

- `URL_SCHEMA = "mysql"`.
- Nutzt `mysql.connector.pooling.MySQLConnectionPool`.
- Dialekt: `mysql.MySQLDialect()`.
- Session: `sessions.MySQLSession`.

---

## EngineFactory

- `configure_factory(db_url, config=None, query_cache=False, name="default")` — Engine konfigurieren.
- `get_engine(name="default")` — Engine abrufen.
- `destroy_engine()` / `destroy_all_engines()` — Engines entfernen.

Singleton:

```python
engine_factory = EngineFactory()
```
