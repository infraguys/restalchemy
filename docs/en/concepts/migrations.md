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

# Migrations concepts

RESTAlchemy uses explicit migration files to evolve the database schema.

Migrations live in a directory (e.g. `examples/migrations/`) and are applied using CLI tools such as `ra-new-migration`, `ra-apply-migration`, `ra-rollback-migration` and `ra-rename-migrations`.

---

## Migration files

Each migration is a Python file with a `migration_step` object:

```python
from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["<prev-migration-file>.py"]

    @property
    def migration_id(self):
        return "<uuid>"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        # Apply changes
        pass

    def downgrade(self, session):
        # Revert changes
        pass


migration_step = MigrationStep()
```

The template for new migrations is located at:

- `restalchemy/storage/sql/migration_templ.tmpl`

and is used by `ra-new-migration`.

---

## Migration identifiers and dependencies

Each migration has:

- A **UUID** (`migration_id` property).
- A **list of dependencies** (`self._depends`), which is a list of migration filenames.
- A **manual flag** (`is_manual` property).

Dependencies form a directed acyclic graph. When applying a migration, its dependencies are applied first.

Special constants:

- `HEAD` — special name meaning "the latest automatic migration".
- `MANUAL` — marker used in migration numbers for manual migrations.

The `MigrationEngine` uses these rules to:

- Resolve partial names to filenames.
- Compute the head migration.
- Ensure that automatic migrations do not depend on manual ones (for `ra-new-migration` without `--manual`).

---

## Migration filenames and numbering

New migrations follow the **new naming scheme**:

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

- `migration_number` — zero-padded number, e.g. `0001`, `0002`, ...
- `message-with-dashes` — taken from `--message`, spaces replaced with `-`.
- `hash` — first 6 characters of the migration UUID.

For manual migrations the number is `MANUAL`:

```text
MANUAL-<message-with-dashes>-<hash>.py
```

The old naming scheme is still supported; the `ra-rename-migrations` tool can convert old names to the new scheme.

If your message starts with a 4-digit number equal in length to the default migration number, that number is used directly as `migration_number`.

---

## Migration state tracking

Applied migrations are tracked in a dedicated table:

- Table name: `ra_migrations`.
- Model: `MigrationModel` (`restalchemy.storage.sql.migrations.MigrationModel`).
- Fields:
  - `uuid` (primary key) — migration UUID.
  - `applied` (boolean) — whether the migration is applied.

The `MigrationEngine` ensures that this table exists and uses it to decide:

- Which migrations still need to be applied.
- Whether a migration can be rolled back.

---

## Automatic vs manual migrations

- **Automatic migrations** (`is_manual == False`):
  - Can depend only on other automatic migrations.
  - Are considered when computing the head migration.
- **Manual migrations** (`is_manual == True`):
  - Often contain non-reversible or environment-specific changes.
  - Are skipped when searching for the head migration.

The `ra-new-migration` command validates that automatic migrations do not depend on manual ones. If such a dependency is found, the command exits with an error.

---

## High-level workflow

At a high level, migrations are used as follows:

1. Define DM models and update them over time.
2. When the schema changes, create a new migration file with `ra-new-migration`.
3. Implement `upgrade()` / `downgrade()` inside the migration file.
4. Apply migrations to a specific database with `ra-apply-migration`.
5. If necessary, roll back migrations with `ra-rollback-migration`.
6. When adopting the new naming scheme, use `ra-rename-migrations` to rename existing migration files and update their dependencies.
