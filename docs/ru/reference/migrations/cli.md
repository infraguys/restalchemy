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

Этот раздел описывает CLI-инструменты для работы с миграциями:

- `ra-new-migration`
- `ra-apply-migration`
- `ra-rollback-migration`
- `ra-rename-migrations`

Все команды используют `oslo_config` и поддерживают как длинные, так и короткие ключи.

---

## `ra-new-migration`

Создание нового файла миграции по шаблону.

### Использование

```bash
ra-new-migration \
  --path <path-to-migrations> \
  --message "1st migration" \
  --depend HEAD \
  [--manual] \
  [--dry-run]
```

### Опции

- `--path` / `-p` (обязательно)
  - Путь к каталогу миграций.
- `--message` / `-m`
  - Текстовое описание; пробелы заменяются на `-` в имени файла.
- `--depend` / `-d`
  - Может указываться несколько раз.
  - Значения — подстрока имени миграции или `HEAD`.
- `--manual`
  - Пометить миграцию как ручную (`is_manual = True`).
- `--dry-run`
  - Показать, что будет создано, без записи файлов.

Если миграция не ручная, команда проверяет, что в зависимостях нет ручных миграций; при нарушении — завершение с кодом `1`.

Файл создаётся на основе `migration_templ.tmpl` с заполнением:

- `migration_id` — UUID.
- `depends` — имена файлов зависимостей.
- `is_manual` — флаг ручной миграции.

---

## `ra-apply-migration`

Применение миграций "вверх" до целевой миграции.

### Использование

```bash
ra-apply-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  [--migration <name-or-HEAD>] \
  [--dry-run]
```

### Опции

- `--path` / `-p` (обязательно)
- `--db-connection`
  - URL подключения к БД (попадает в `CONF.db.connection_url`).
- `--migration` / `-m`
  - Целевая миграция или `HEAD`.
  - По умолчанию: `HEAD` (последняя автоматическая миграция).
- `--dry-run`
  - Прогон без вызова `upgrade()`.

### Поведение

- Настраивает SQL-движок: `engine_factory.configure_factory(db_url=CONF.db.connection_url)`.
- Создаёт `MigrationEngine(migrations_path=CONF.path)`.
- Вычисляет целевую миграцию (учитывая `HEAD`).
- Применяет все необходимые миграции (с учётом зависимостей), вызывая `upgrade()` и помечая их как `applied=True`.

---

## `ra-rollback-migration`

Откат миграций до целевой миграции.

### Использование

```bash
ra-rollback-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  --migration <name> \
  [--dry-run]
```

### Опции

- `--path` / `-p` (обязательно)
- `--db-connection` (обязательно)
- `--migration` / `-m` (обязательно)
  - Имя целевой миграции.
- `--dry-run`
  - Прогон без вызова `downgrade()`.

### Поведение

- Аналогично `ra-apply-migration` настраивает движок.
- Использует `MigrationEngine.rollback_migration()` для:
  - Инициализации таблицы `ra_migrations`.
  - Загрузки контроллеров миграций.
  - Отката зависимых миграций и затем целевой миграции.

---

## `ra-rename-migrations`

Переименование файлов миграций в новый формат и обновление зависимостей.

### Использование

```bash
ra-rename-migrations --path <path-to-migrations>
```

### Опции

- `--path` / `-p` (обязательно)
  - Путь к каталогу миграций.

### Поведение

- Создаёт `MigrationEngine` для указанного пути.
- Вызывает `engine.get_all_migrations()` и получает для каждой миграции:
  - индекс,
  - UUID,
  - зависимости,
  - признак `is_manual`.
- Для каждого файла:
  - Формирует новое имя:
    - Автоматическая: `<index>-<oldname>-<hash>.py`.
    - Ручная: `MANUAL-<oldname>-<hash>.py`.
  - Переименовывает файл на диске.
  - Обновляет зависимости внутри файла (подменяет старые имена на новые).

Рекомендуется выполнить один раз при переходе на новую схему имён.
