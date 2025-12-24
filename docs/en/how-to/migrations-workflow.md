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

# Migrations workflow

This guide describes a practical workflow for managing SQL schema migrations in RESTAlchemy.

You will learn how to:

- Organise migration files.
- Create new migrations with `ra-new-migration`.
- Apply migrations with `ra-apply-migration`.
- Roll back migrations with `ra-rollback-migration`.
- Rename existing migrations to the new naming scheme with `ra-rename-migrations`.

---

## 1. Directory structure

Choose a directory for migrations, for example:

```text
myservice/
  migrations/
    ... migration files ...
```

The examples in this repository use:

- `examples/migrations/`

All `ra-*` commands use the `--path` / `-p` option to point to the migrations directory.

---

## 2. Creating a new migration

Use the `ra-new-migration` command:

```bash
ra-new-migration \
  --path examples/migrations/ \
  --message "create users table" \
  --depend HEAD
```

Options:

- `--path` / `-p` — required. Path to the migrations folder.
- `--message` / `-m` — short description; spaces are converted to `-`.
- `--depend` / `-d` — zero or more dependencies (filenames or `HEAD`).
- `--manual` — mark migration as manual.
- `--dry-run` — show what would be created without writing files.

Typical cases:

- **Automatic migration depending on HEAD**:
  - `--depend HEAD`
  - Good for linear chains of migrations.
- **Manual migration**:
  - `--manual`
  - Use when changes are environment-specific or not automatically reversible.

After running the command, a new file is created in the migrations folder using the naming scheme:

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

The file contains a `MigrationStep` class with empty `upgrade()` and `downgrade()` methods. You must fill them with actual SQL (or DM/Storage) changes using the provided `session` object.

---

## 3. Implementing upgrade and downgrade

Inside the generated file, implement the migration logic.

Example:

```python
from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["0001-create-users-abcdef.py"]

    @property
    def migration_id(self):
        return "...uuid..."

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        session.execute(
            """CREATE TABLE users (
                   uuid CHAR(36) PRIMARY KEY,
                   name VARCHAR(255) NOT NULL
               )""",
            None,
        )

    def downgrade(self, session):
        self._delete_table_if_exists(session, "users")


migration_step = MigrationStep()
```

Notes:

- `session.execute(statement, values)` runs raw SQL.
- Helper methods in `AbstractMigrationStep`:
  - `_delete_table_if_exists(session, table_name)`
  - `_delete_trigger_if_exists(session, trigger_name)`
  - `_delete_view_if_exists(session, view_name)`

You can also combine raw SQL with higher‑level Storage/DM logic if appropriate.

---

## 4. Applying migrations

Use `ra-apply-migration` to upgrade the database:

```bash
ra-apply-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test
```

Options:

- `--path` / `-p` — required. Path to migrations.
- `--db-connection` — database connection URL (registered as `db.connection_url`).
- `--migration` / `-m` — target migration name or short name; defaults to `HEAD`.
- `--dry-run` — dry run (no actual changes).

Without `-m`, the command will:

- Compute the head automatic migration (`HEAD`).
- Apply all unapplied automatic migrations up to this head.

With `-m X`:

- Apply all unapplied migrations needed to reach migration `X`.

If a migration is already applied, it is skipped with a warning.

---

## 5. Rolling back migrations

Use `ra-rollback-migration` to downgrade the database to a specific migration:

```bash
ra-rollback-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test \
  --migration 0003-add-index
```

Options:

- `--path` / `-p` — required. Path to migrations.
- `--db-connection` — database connection URL.
- `--migration` / `-m` — required. Target migration name.
- `--dry-run` — dry run (no changes).

The rollback process:

- For each migration that depends on the target migration, roll it back first (reverse dependency order).
- Then run `downgrade()` for the target migration itself and mark it as not applied.

If a migration is already not applied, it is skipped with a warning.

---

## 6. Renaming migrations to the new naming scheme

Use `ra-rename-migrations` to convert existing migration filenames to the new scheme:

```bash
ra-rename-migrations --path examples/migrations/
```

The tool will:

- Analyse all migration files and compute an index for each migration.
- Suggest new filenames of the form:

  - Automatic: `0001-oldname-<hash>.py`
  - Manual: `MANUAL-oldname-<hash>.py`

- Rename files on disk.
- Update dependencies inside migration files to use the new filenames.

This is useful when migrating from old short names to the new `<number>-<message>-<hash>.py` format.

---

## 7. Recommended practice

- Store migration files under version control.
- Use meaningful `--message` values; they become part of filenames.
- Prefer automatic migrations for typical schema changes; reserve manual migrations for truly special cases.
- Always run migrations in CI against a test database before applying to production.
