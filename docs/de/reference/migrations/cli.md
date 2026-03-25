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

# Migrations CLI Referenz

Dieser Abschnitt beschreibt die CLI-Befehle zur Verwaltung von Migrationen:

- `ra-new-migration`
- `ra-apply-migration`
- `ra-rollback-migration`
- `ra-rename-migrations`

---

## `ra-new-migration`

Neue Migrationsdatei erzeugen.

```bash
ra-new-migration \
  --path <path-to-migrations> \
  --message "1st migration" \
  --depend HEAD \
  [--manual] \
  [--dry-run]
```

Wichtigste Optionen:

- `--path` / `-p` — Migrationsverzeichnis.
- `--message` / `-m` — Beschreibung (Leerzeichen → `-`).
- `--depend` / `-d` — Abhängigkeiten (mehrfach möglich, inkl. `HEAD`).
- `--manual` — markiert Migration als manuell.
- `--dry-run` — nur anzeigen, nichts schreiben.

---

## `ra-apply-migration`

Migrationen "nach oben" anwenden.

```bash
ra-apply-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  [--migration <name-or-HEAD>] \
  [--dry-run]
```

- `--path` / `-p` — Pfad.
- `--db-connection` — DB-URL.
- `--migration` / `-m` — Zielmigration (`HEAD` als Default).
- `--dry-run` — ohne Änderungen.

---

## `ra-rollback-migration`

Migrationen zurückrollen.

```bash
ra-rollback-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  --migration <name> \
  [--dry-run]
```

- `--path` / `-p` — Pfad.
- `--db-connection` — DB-URL.
- `--migration` / `-m` — Zielmigration.
- `--dry-run` — ohne Änderungen.

---

## `ra-rename-migrations`

Migrationen auf neues Namensschema umstellen.

```bash
ra-rename-migrations --path <path-to-migrations>
```

- `--path` / `-p` — Pfad.

Benennt Dateien um und passt Abhängigkeiten im Code an.
