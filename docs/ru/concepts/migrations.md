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

# Концепции миграций

RESTAlchemy использует явные файлы миграций для эволюции схемы базы данных.

Миграции располагаются в каталоге (например, `examples/migrations/`) и применяются с помощью CLI-инструментов: `ra-new-migration`, `ra-apply-migration`, `ra-rollback-migration`, `ra-rename-migrations`.

---

## Файлы миграций

Каждая миграция — это Python-файл с объектом `migration_step`:

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

Шаблон для новых миграций находится в файле:

- `restalchemy/storage/sql/migration_templ.tmpl`

и используется командой `ra-new-migration`.

---

## Идентификаторы и зависимости миграций

У каждой миграции есть:

- **UUID** (`migration_id`).
- **Список зависимостей** (`self._depends`) — список имён файлов миграций.
- **Флаг ручной миграции** (`is_manual`).

Зависимости образуют ориентированный ацикличный граф. При применении миграции сначала применяются все её зависимости.

Специальные константы:

- `HEAD` — обозначает "последнюю автоматическую миграцию".
- `MANUAL` — маркер, используемый в номерах файлов для ручных миграций.

`MigrationEngine` использует эти правила, чтобы:

- Разрешать частичное имя до полного имени файла.
- Вычислять head-миграцию.
- Проверять, что автоматические миграции не зависят от ручных (в `ra-new-migration` без `--manual`).

---

## Имена файлов и нумерация миграций

Новые миграции используют **новую схему имён**:

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

- `migration_number` — число с ведущими нулями, например `0001`, `0002`, ...
- `message-with-dashes` — строка из `--message`, где пробелы заменены на `-`.
- `hash` — первые 6 символов UUID миграции.

Для ручных миграций номер равен `MANUAL`:

```text
MANUAL-<message-with-dashes>-<hash>.py
```

Старая схема имён по-прежнему поддерживается; команда `ra-rename-migrations` может переименовать старые файлы в новый формат и обновить зависимости.

Если сообщение начинается с 4-значного числа (длины по умолчанию для номера миграции), это число используется как `migration_number` напрямую.

---

## Отслеживание состояния миграций

Применённые миграции хранятся в отдельной таблице:

- Имя таблицы: `ra_migrations`.
- Модель: `MigrationModel` (`restalchemy.storage.sql.migrations.MigrationModel`).
- Поля:
  - `uuid` (PK) — UUID миграции.
  - `applied` (bool) — признак применения миграции.

`MigrationEngine` гарантирует существование этой таблицы и использует её, чтобы:

- Определять, какие миграции ещё не применены.
- Проверять, можно ли выполнить откат миграции.

---

## Автоматические и ручные миграции

- **Автоматические миграции** (`is_manual == False`):
  - Могут зависеть только от других автоматических миграций.
  - Учитываются при вычислении head-миграции.
- **Ручные миграции** (`is_manual == True`):
  - Часто содержат нестандартные/необратимые изменения.
  - Не используются при поиске head-миграции.

Команда `ra-new-migration` проверяет, что автоматическая миграция не ссылается на ручные миграции в зависимостях. При нарушении этого правила выполнение завершается с ошибкой.

---

## Общий рабочий процесс

1. Вы описываете DM-модели и со временем изменяете их.
2. При изменении схемы БД создаёте новый файл миграции через `ra-new-migration`.
3. Реализуете `upgrade()` / `downgrade()` в файле миграции.
4. Применяете миграции к конкретной базе через `ra-apply-migration`.
5. При необходимости откатываете миграции с помощью `ra-rollback-migration`.
6. При переходе на новую схему имён используете `ra-rename-migrations` для переименования существующих файлов и обновления зависимостей.
