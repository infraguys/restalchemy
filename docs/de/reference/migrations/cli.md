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

Alle Befehle nutzen intern `oslo_config` und unterstützen sowohl lange als auch kurze Optionen.

---

## `ra-new-migration`

Erzeugt eine neue Migrationsdatei auf Basis eines Templates.

### Verwendung

```bash
ra-new-migration \
  --path <path-to-migrations> \
  --message "1st migration" \
  --depend HEAD \
  [--manual] \
  [--dry-run]
```

### Optionen

- `--path` / `-p` (erforderlich)
  - Pfad zum Migrationsverzeichnis.
- `--message` / `-m`
  - Menschenlesbare Beschreibung; Leerzeichen werden im Dateinamen durch `-` ersetzt.
- `--depend` / `-d`
  - Kann mehrfach angegeben werden.
  - Zulässige Werte sind entweder:
    - ein Teilstring eines Migrationsdateinamens; oder
    - der Sonderwert `HEAD`.
- `--manual`
  - Markiert die Migration als manuell (`is_manual = True`).
- `--dry-run`
  - Zeigt an, was erzeugt würde, ohne Dateien zu schreiben.

Ist die Migration nicht manuell, prüft das Werkzeug, dass automatische Migrationen nicht von manuellen abhängen; andernfalls endet es mit Exit-Code `1`.

Die Datei wird aus `migration_templ.tmpl` erzeugt und gefüllt mit:

- `migration_id` — UUID.
- `depends` — aufgelöste Dateinamen der Abhängigkeiten.
- `is_manual` — Boolean.

---

## `ra-apply-migration`

Wendet Migrationen bis zu einer Zielmigration an.

### Verwendung

```bash
ra-apply-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  [--migration <name-or-HEAD>] \
  [--dry-run]
```

### Optionen

- `--path` / `-p` (erforderlich)
  - Pfad zu den Migrationen.
- `--db-connection`
  - URL der Datenbankverbindung, über `config_opts.register_common_db_opts` als `CONF.db.connection_url` abgelegt.
- `--migration` / `-m`
  - Name oder Kurzname der Zielmigration.
  - Default: `HEAD` (die neueste automatische Migration).
- `--dry-run`
  - Trockenlauf, ohne `upgrade()` auszuführen.

### Verhalten

- Konfiguriert die SQL-Engine über `engine_factory.configure_factory(db_url=CONF.db.connection_url)`.
- Verwendet `MigrationEngine(migrations_path=CONF.path)`, um:
  - `HEAD` bei Bedarf aufzulösen.
  - Alle erforderlichen Migrationen anzuwenden (Abhängigkeiten zuerst).
  - `upgrade()` aufzurufen und Migrationen als angewendet zu markieren.

---

## `ra-rollback-migration`

Rollt Migrationen bis zu einer Zielmigration zurück.

### Verwendung

```bash
ra-rollback-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  --migration <name> \
  [--dry-run]
```

### Optionen

- `--path` / `-p` (erforderlich)
- `--db-connection` (erforderlich)
- `--migration` / `-m` (erforderlich)
  - Name der Zielmigration.
- `--dry-run`
  - Trockenlauf, ohne `downgrade()` auszuführen.

### Verhalten

- Konfiguriert die SQL-Engine analog zu `ra-apply-migration`.
- Verwendet `MigrationEngine.rollback_migration()`, das:
  - Sicherstellt, dass die Tabelle `ra_migrations` existiert.
  - Die Migrations-Controller lädt.
  - Zuerst abhängige Migrationen zurückrollt, danach die Zielmigration.

---

## `ra-rename-migrations`

Benennt Migrationsdateien auf das neue Namensschema um und aktualisiert die Abhängigkeiten.

### Verwendung

```bash
ra-rename-migrations --path <path-to-migrations>
```

### Optionen

- `--path` / `-p` (erforderlich)
  - Pfad zu den Migrationen.

### Verhalten

- Erzeugt eine `MigrationEngine` für den angegebenen Pfad.
- Ruft `engine.get_all_migrations()` auf, um die Metadaten zu erhalten:
  - `index`, `uuid`, `depends`, `is_manual`.
- Für jede Datei:
  - Schlägt einen neuen Dateinamen vor:
    - Automatisch: `<index>-<oldname>-<uuid_prefix>.py`.
    - Manuell: `MANUAL-<oldname>-<uuid_prefix>.py`.
  - Benennt die Datei um.
  - Hat die Migration Abhängigkeiten:
    - Öffnet die neue Datei.
    - Schreibt die Abhängigkeits-Strings von den alten auf die vorgeschlagenen neuen Dateinamen um.

Dies ist ein einmaliger Werkzeugschritt, um bestehende Projekte auf die neue Namenskonvention umzustellen.
