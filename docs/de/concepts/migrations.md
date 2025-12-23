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

# Migrationskonzepte

RESTAlchemy verwendet explizite Migrationsdateien, um das Datenbankschema weiterzuentwickeln.

Migrationen liegen in einem Verzeichnis (z.B. `examples/migrations/`) und werden über CLI-Tools wie `ra-new-migration`, `ra-apply-migration`, `ra-rollback-migration` und `ra-rename-migrations` ausgeführt.

---

## Migrationsdateien

Jede Migration ist eine Python-Datei mit einem `migration_step` Objekt:

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
        pass

    def downgrade(self, session):
        pass


migration_step = MigrationStep()
```

Die Vorlage für neue Migrationen liegt in:

- `restalchemy/storage/sql/migration_templ.tmpl`

und wird von `ra-new-migration` verwendet.

---

## Identifikatoren und Abhängigkeiten

Jede Migration besitzt:

- Eine **UUID** (`migration_id`).
- Eine **Abhängigkeitsliste** (`self._depends`) mit Dateinamen anderer Migrationen.
- Ein Flag `is_manual`.

Abhängigkeiten bilden einen gerichteten azyklischen Graphen. Beim Anwenden einer Migration werden zuerst alle Abhängigkeiten angewendet.

Spezielle Konstanten:

- `HEAD` — steht für die „letzte automatische Migration“.
- `MANUAL` — Kennzeichnung für manuelle Migrationen im Dateinamen.

Der `MigrationEngine` nutzt diese Informationen, um:

- Teilnamen auf konkrete Dateinamen abzubilden.
- Die Head-Migration zu bestimmen.
- Sicherzustellen, dass automatische Migrationen nicht von manuellen abhängen.

---

## Dateinamen und Nummerierung

Neuer Namensstandard für Migrationen:

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

- `migration_number` — Zahl mit führenden Nullen (`0001`, `0002`, ...).
- `message-with-dashes` — aus `--message`, Leerzeichen → `-`.
- `hash` — erste 6 Zeichen der UUID.

Für manuelle Migrationen:

```text
MANUAL-<message-with-dashes>-<hash>.py
```

Der alte Namensstandard wird weiterhin unterstützt; `ra-rename-migrations` kann alte Dateien auf das neue Schema umbenennen und Abhängigkeiten anpassen.

Wenn die Nachricht mit einer 4-stelligen Zahl beginnt, wird diese Zahl direkt als `migration_number` verwendet.

---

## Statusverfolgung

Angewendete Migrationen werden in der Tabelle `ra_migrations` verfolgt:

- Modell: `MigrationModel`.
- Spalten:
  - `uuid` — Primärschlüssel, Migration-UUID.
  - `applied` — Bool, angewendet oder nicht.

`MigrationEngine` sorgt für das Vorhandensein der Tabelle und nutzt sie, um:

- Nicht angewendete Migrationen zu finden.
- Zu entscheiden, ob ein Rollback möglich ist.

---

## Automatische vs. manuelle Migrationen

- **Automatische Migrationen** (`is_manual == False`):
  - Dürfen nur von anderen automatischen Migrationen abhängen.
  - Werden bei der Bestimmung der Head-Migration berücksichtigt.
- **Manuelle Migrationen** (`is_manual == True`):
  - Enthalten oft spezielle oder schwer rückgängig zu machende Änderungen.
  - Werden bei der Head-Berechnung ausgelassen.

`ra-new-migration` prüft, dass automatische Migrationen keine manuellen in ihren Abhängigkeiten haben; andernfalls bricht der Befehl mit Fehler ab.

---

## Typischer Workflow

1. DM-Modelle definieren und im Laufe der Zeit anpassen.
2. Bei Schemaänderungen neue Migration per `ra-new-migration` erzeugen.
3. `upgrade()` / `downgrade()` in der Migrationsdatei implementieren.
4. Migrationen mit `ra-apply-migration` anwenden.
5. Falls nötig, mit `ra-rollback-migration` zurückrollen.
6. Beim Umstieg auf das neue Namensschema `ra-rename-migrations` verwenden.
