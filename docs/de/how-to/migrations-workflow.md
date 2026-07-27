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

Wählen Sie ein Verzeichnis für die Migrationen, zum Beispiel:

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

Verwenden Sie den Befehl `ra-new-migration`:

```bash
ra-new-migration \
  --path examples/migrations/ \
  --message "create users table" \
  --depend HEAD
```

Optionen:

- `--path` / `-p` — erforderlich. Pfad zum Migrationsverzeichnis.
- `--message` / `-m` — kurze Beschreibung; Leerzeichen werden zu `-`.
- `--depend` / `-d` — null oder mehr Abhängigkeiten (Dateinamen oder `HEAD`).
- `--manual` — markiert die Migration als manuell.
- `--dry-run` — zeigt an, was passieren würde, ohne Dateien zu schreiben.

Typische Fälle:

- **Automatische Migration, die von HEAD abhängt**:
  - `--depend HEAD`
  - Geeignet für lineare Migrationsketten.
- **Manuelle Migration**:
  - `--manual`
  - Sinnvoll, wenn Änderungen umgebungsspezifisch oder nicht automatisch umkehrbar sind.

Nach dem Befehl wird eine neue Datei im Format

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

angelegt. Sie enthält eine `MigrationStep`-Klasse mit leeren Methoden `upgrade()` und `downgrade()`. Diese müssen Sie mit den tatsächlichen SQL- (oder DM-/Storage-)Änderungen füllen und dabei das übergebene `session`-Objekt verwenden.

---

## 3. upgrade/downgrade implementieren

In der generierten Datei implementieren Sie die Migrationslogik.

Beispiel:

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

Hinweise:

- `session.execute(statement, values)` führt rohes SQL aus.
- Hilfsmethoden von `AbstractMigrationStep`:
  - `_delete_table_if_exists(session, table_name)`
  - `_delete_trigger_if_exists(session, trigger_name)`
  - `_delete_view_if_exists(session, view_name)`

Sie können rohes SQL bei Bedarf auch mit höherliegender Storage-/DM-Logik kombinieren.

---

## 4. Migrationen anwenden

Mit `ra-apply-migration` bringen Sie die Datenbank auf den neuesten Stand:

```bash
ra-apply-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test
```

Optionen:

- `--path` / `-p` — erforderlich. Pfad zu den Migrationen.
- `--db-connection` — URL der Datenbankverbindung (registriert als `db.connection_url`).
- `--migration` / `-m` — Name oder Kurzname der Zielmigration; Default ist `HEAD`.
- `--dry-run` — Trockenlauf (keine echten Änderungen).

Ohne `-m` wird der Befehl:

- Die automatische Head-Migration (`HEAD`) ermitteln.
- Alle noch nicht angewendeten automatischen Migrationen bis zu diesem Head anwenden.

Mit `-m X`:

- Werden alle noch nicht angewendeten Migrationen angewendet, die nötig sind, um Migration `X` zu erreichen.

Ist eine Migration bereits angewendet, wird sie mit einer Warnung übersprungen.

---

## 5. Migrationen zurückrollen

Mit `ra-rollback-migration` setzen Sie die Datenbank auf eine bestimmte Migration zurück:

```bash
ra-rollback-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test \
  --migration 0003-add-index
```

Optionen:

- `--path` / `-p` — erforderlich. Pfad zu den Migrationen.
- `--db-connection` — URL der Datenbankverbindung.
- `--migration` / `-m` — erforderlich. Name der Zielmigration.
- `--dry-run` — Trockenlauf (keine Änderungen).

Der Rollback-Ablauf:

- Jede Migration, die von der Zielmigration abhängt, wird zuerst zurückgerollt (umgekehrte Abhängigkeitsreihenfolge).
- Danach läuft `downgrade()` für die Zielmigration selbst, und sie wird als nicht angewendet markiert.

Ist eine Migration bereits nicht angewendet, wird sie mit einer Warnung übersprungen.

---

## 6. Migrationen auf das neue Namensschema umstellen

Mit `ra-rename-migrations` überführen Sie bestehende Migrationsdateinamen in das neue Schema:

```bash
ra-rename-migrations --path examples/migrations/
```

Das Werkzeug wird:

- Alle Migrationsdateien analysieren und für jede Migration einen Index berechnen.
- Neue Dateinamen vorschlagen, und zwar in der Form:

  - Automatisch: `0001-altname-<hash>.py`
  - Manuell: `MANUAL-altname-<hash>.py`

- Die Dateien auf der Platte umbenennen.
- Die Abhängigkeiten in den Migrationsdateien auf die neuen Dateinamen aktualisieren.

Das ist hilfreich beim Umstieg von alten Kurznamen auf das neue Format `<nummer>-<message>-<hash>.py`.

---

## 7. Empfohlene Praxis

- Halten Sie die Migrationsdateien unter Versionskontrolle.
- Verwenden Sie aussagekräftige `--message`-Texte; sie werden Teil der Dateinamen.
- Bevorzugen Sie automatische Migrationen für typische Schemaänderungen und heben Sie sich manuelle Migrationen für wirklich besondere Fälle auf.
- Lassen Sie Migrationen immer erst in der CI gegen eine Testdatenbank laufen, bevor Sie sie in der Produktion anwenden.
