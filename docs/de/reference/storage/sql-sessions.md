# SQL Sessions und Transaktionen

Modul: `restalchemy.storage.sql.sessions`

Definiert Sessions, Query-Cache und Helfer für Transaktionen.

---

## SessionQueryCache

- Session-lokaler Cache für `get_all()` / `query()`.

---

## PgSQLSession und MySQLSession

- Wrappen DB-Verbindungen und Cursors.
- Methoden: `execute()`, `execute_many()`, `commit()`, `rollback()`, `close()`.
- `batch_insert(models)` / `batch_delete(models)` für Bulk-Operationen.

---

## session_manager

- `engine.session_manager()` öffnet/verwaltet eine Session und Transaktion.
- Bei Erfolg: `commit()`, bei Fehler: `rollback()`.

Beispiel:

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    foo = FooModel(foo_field1=42)
    foo.save(session=session)
```

---

## SessionThreadStorage

- Thread-lokale Speicherung von Sessions.
- Ermöglicht Wiederverwendung derselben Session in einem Thread.
