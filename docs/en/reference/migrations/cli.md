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

# Migrations CLI reference

This page documents the CLI tools used to manage migrations:

- `ra-new-migration`
- `ra-apply-migration`
- `ra-rollback-migration`
- `ra-rename-migrations`

All commands use `oslo_config` under the hood and support both long and short options.

---

## `ra-new-migration`

Create a new migration file based on a template.

### Usage

```bash
ra-new-migration \
  --path <path-to-migrations> \
  --message "1st migration" \
  --depend HEAD \
  [--manual] \
  [--dry-run]
```

### Options

- `--path` / `-p` (required)
  - Path to the migrations folder.
- `--message` / `-m`
  - Human-readable description; spaces are replaced with `-` in filenames.
- `--depend` / `-d`
  - May be specified multiple times.
  - Values are either:
    - a substring of a migration filename; or
    - the special value `HEAD`.
- `--manual`
  - Mark the migration as manual (`is_manual = True`).
- `--dry-run`
  - Print what would be created without writing files.

If the migration is not manual, the tool validates that automatic migrations do not depend on manual ones; otherwise it exits with code `1`.

The file is created from `migration_templ.tmpl` and filled with:

- `migration_id` — UUID.
- `depends` — resolved dependency filenames.
- `is_manual` — boolean.

---

## `ra-apply-migration`

Apply migrations up to a target migration.

### Usage

```bash
ra-apply-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  [--migration <name-or-HEAD>] \
  [--dry-run]
```

### Options

- `--path` / `-p` (required)
  - Path to migrations.
- `--db-connection`
  - Database connection URL, stored as `CONF.db.connection_url` via `config_opts.register_common_db_opts`.
- `--migration` / `-m`
  - Target migration name or short name.
  - Default: `HEAD` (latest automatic migration).
- `--dry-run`
  - Perform a dry run without executing `upgrade()`.

### Behavior

- Configures SQL engine via `engine_factory.configure_factory(db_url=CONF.db.connection_url)`.
- Uses `MigrationEngine(migrations_path=CONF.path)` to:
  - Resolve `HEAD` if needed.
  - Apply all required migrations (dependencies first).
  - Call `upgrade()` and mark migrations as applied.

---

## `ra-rollback-migration`

Roll back migrations down to a target migration.

### Usage

```bash
ra-rollback-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  --migration <name> \
  [--dry-run]
```

### Options

- `--path` / `-p` (required)
- `--db-connection` (required)
- `--migration` / `-m` (required)
  - Target migration name.
- `--dry-run`
  - Perform a dry run without executing `downgrade()`.

### Behavior

- Configures SQL engine similar to `ra-apply-migration`.
- Uses `MigrationEngine.rollback_migration()` which:
  - Ensures `ra_migrations` table exists.
  - Loads migration controllers.
  - Rolls back dependent migrations first, then the target.

---

## `ra-rename-migrations`

Rename migration files to the new naming scheme and update dependencies.

### Usage

```bash
ra-rename-migrations --path <path-to-migrations>
```

### Options

- `--path` / `-p` (required)
  - Path to migrations.

### Behavior

- Builds a `MigrationEngine` for the given path.
- Calls `engine.get_all_migrations()` to obtain metadata:
  - `index`, `uuid`, `depends`, `is_manual`.
- For each file:
  - Suggests a new filename:
    - Automatic: `<index>-<oldname>-<uuid_prefix>.py`.
    - Manual: `MANUAL-<oldname>-<uuid_prefix>.py`.
  - Renames the file.
  - If the migration has dependencies:
    - Opens the new file.
    - Rewrites dependency strings from old filenames to the suggested new filenames.

This is a one-time tooling step to migrate existing projects to the new naming convention.
