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
