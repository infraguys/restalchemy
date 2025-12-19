# Storage reference

This section describes the storage layer types and functions used to persist DM models.

Most user-facing code lives in `restalchemy.storage.sql.*` and is used together with DM models and the API layer.

---

## Modules

- `restalchemy.storage.base`
  - Abstract interfaces for storable models and collections.
- `restalchemy.storage.exceptions`
  - Exceptions raised by the storage layer.
- `restalchemy.storage.sql.engines`
  - SQL engine factory and concrete engines for MySQL and PostgreSQL.
- `restalchemy.storage.sql.sessions`
  - Database sessions, transaction helpers and query cache.
- `restalchemy.storage.sql.orm`
  - ORM-like mixins and `ObjectCollection` used by DM models.
- `restalchemy.storage.sql.tables`
  - Table abstraction used by ORM and dialects.
- `restalchemy.storage.sql.dialect.*`
  - Dialect-specific query builders.

---

## Entry points for typical usage

For most applications you only need to:

1. Configure an engine:

   ```python
   from restalchemy.storage.sql import engines

   engines.engine_factory.configure_factory(
       db_url="mysql://user:password@127.0.0.1:3306/test",
   )
   ```

2. Define DM models that inherit from `orm.SQLStorableMixin` and set `__tablename__`.

3. Use:

   - `Model.objects.get_all()` / `Model.objects.get_one()` for reads.
   - `.save()` and `.delete()` on model instances for writes.

The following pages describe these components in more detail:

- [SQL engines](sql-engines.md)
- [SQL ORM mixins and collections](sql-orm.md)
- [SQL sessions and transactions](sql-sessions.md)
