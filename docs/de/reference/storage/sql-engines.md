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

### Verbindungs-Timeouts

`register_postgresql_db_opts()` registriert Einstellungen für Verbindungs-,
Server- und TCP-Timeouts. Zeiträume werden in Sekunden angegeben; `0` behält
den jeweiligen Standardwert von libpq, PostgreSQL oder dem Betriebssystem bei.

- `connection_connect_timeout`: Zeit zum Aufbau einer Verbindung.
- `connection_statement_timeout`: maximale Ausführungszeit einer Anweisung.
- `connection_transaction_timeout`: maximale Transaktionsdauer; erfordert
  PostgreSQL 17 oder neuer.
- `connection_idle_in_transaction_session_timeout`: maximale Leerlaufzeit einer
  Sitzung innerhalb einer Transaktion.
- `connection_tcp_user_timeout`: maximale Zeit für unbestätigte TCP-Daten.
- `connection_keepalives_idle`, `connection_keepalives_interval` und
  `connection_keepalives_count`: Parameter zur TCP-Keepalive-Erkennung.

Beispiel:

```ini
[db]
connection_connect_timeout = 30
connection_statement_timeout = 240
connection_transaction_timeout = 300
connection_idle_in_transaction_session_timeout = 240
connection_tcp_user_timeout = 300
connection_keepalives_idle = 60
connection_keepalives_interval = 30
connection_keepalives_count = 5
```

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
