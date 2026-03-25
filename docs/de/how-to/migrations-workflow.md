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

# Migrations-Workflow

Dieser Leitfaden beschreibt einen praktischen Workflow für SQL-Migrationen in RESTAlchemy.

Sie lernen:

- Wie Sie ein Migrationsverzeichnis organisieren.
- Wie Sie neue Migrationen mit `ra-new-migration` erstellen.
- Wie Sie Migrationen mit `ra-apply-migration` anwenden.
- Wie Sie Migrationen mit `ra-rollback-migration` zurückrollen.
- Wie Sie alte Migrationen auf das neue Namensschema mit `ra-rename-migrations` umstellen.

---

## 1. Verzeichnisstruktur

Beispiel:

```text
myservice/
  migrations/
    ... migration files ...
```

Im Repository werden u.a. verwendet:

- `examples/migrations/`

Alle `ra-*` Befehle nutzen `--path` / `-p` für das Migrationsverzeichnis.

---

## 2. Neue Migration erstellen

```bash
ra-new-migration \
  --path examples/migrations/ \
  --message "create users table" \
  --depend HEAD
```

Wichtige Optionen:

- `--path` / `-p` — Pfad zum Migrationsverzeichnis.
- `--message` / `-m` — Beschreibung, Leerzeichen → `-`.
- `--depend` / `-d` — Abhängigkeiten (Dateinamen oder `HEAD`).
- `--manual` — markiert die Migration als manuell.
- `--dry-run` — zeigt an, was passieren würde, ohne Dateien zu schreiben.

Nach dem Befehl wird eine neue Datei im Format

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

angelegt. Sie enthält `MigrationStep` mit leeren `upgrade()` / `downgrade()` Methoden.

---

## 3. upgrade/downgrade implementieren

In der generierten Datei implementieren Sie die Schemaänderungen.

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

Hilfsfunktionen von `AbstractMigrationStep`:

- `_delete_table_if_exists(session, table_name)`
- `_delete_trigger_if_exists(session, trigger_name)`
- `_delete_view_if_exists(session, view_name)`

---

## 4. Migrationen anwenden

```bash
ra-apply-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test
```

- `--path` / `-p` — Pfad zu Migrationen.
- `--db-connection` — DB-URL.
- `--migration` / `-m` — Zielmigration (Default: `HEAD`).
- `--dry-run` — ohne echte Änderungen.

Ohne `-m` werden alle noch nicht angewendeten automatischen Migrationen bis zur HEAD-Migration ausgeführt.

---

## 5. Migrationen zurückrollen

```bash
ra-rollback-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test \
  --migration 0003-add-index
```

- `--path` / `-p` — Pfad.
- `--db-connection` — DB-URL.
- `--migration` / `-m` — Zielmigration.
- `--dry-run` — ohne Änderungen.

Zuerst werden abhängige Migrationen zurückgerollt, dann die Zielmigration selbst.

---

## 6. Migrationen umbenennen

```bash
ra-rename-migrations --path examples/migrations/
```

- Analysiert alle Migrationen und berechnet einen Index.
- Schlägt neue Namen vor (`0001-altname-<hash>.py`, `MANUAL-altname-<hash>.py`).
- Bennent Dateien um und aktualisiert Abhängigkeiten.

---

## 7. Best Practices

- Migrationsverzeichnis unter Versionskontrolle halten.
- Aussagekräftige `--message` Texte verwenden.
- Automatische Migrationen für Standardschemaänderungen, manuelle für Spezialfälle.
- Migrationen zunächst in Test-/CI-Umgebung laufen lassen.
