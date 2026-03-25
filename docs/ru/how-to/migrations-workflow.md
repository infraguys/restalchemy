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

В этом руководстве описан практический процесс работы с миграциями схемы БД в RESTAlchemy.

Вы узнаете, как:

- Организовать каталог миграций.
- Создавать новые миграции через `ra-new-migration`.
- Применять миграции с помощью `ra-apply-migration`.
- Откатывать миграции через `ra-rollback-migration`.
- Переименовывать существующие миграции в новый формат с `ra-rename-migrations`.

---

## 1. Структура каталога

Выберите каталог для миграций, например:

```text
myservice/
  migrations/
    ... migration files ...
```

В репозитории примеры используют:

- `examples/migrations/`

Во всех `ra-*` командах путь указывается через опцию `--path` / `-p`.

---

## 2. Создание новой миграции

Команда `ra-new-migration`:

```bash
ra-new-migration \
  --path examples/migrations/ \
  --message "create users table" \
  --depend HEAD
```

Основные опции:

- `--path` / `-p` — ОБЯЗАТЕЛЬНО. Путь к каталогу миграций.
- `--message` / `-m` — текстовое описание; пробелы заменяются на `-`.
- `--depend` / `-d` — ноль или более зависимостей (имена файлов или `HEAD`).
- `--manual` — пометить миграцию как ручную.
- `--dry-run` — создать миграцию "на сухую" без записи файла.

Типичные сценарии:

- **Автоматическая миграция от HEAD**:
  - `--depend HEAD`
  - Удобно для линейной цепочки миграций.
- **Ручная миграция**:
  - `--manual`
  - Используется для нестандартных или труднообратимых изменений.

После выполнения команды в каталоге появится новый файл миграции с именем вида:

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

Файл содержит класс `MigrationStep` с пустыми методами `upgrade()` и `downgrade()`. Именно в них нужно реализовать изменения схемы, используя переданный `session`.

---

## 3. Реализация upgrade/downgrade

В сгенерированном файле вы реализуете логику миграции.

Пример:

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

Полезные методы `AbstractMigrationStep`:

- `_delete_table_if_exists(session, table_name)`
- `_delete_trigger_if_exists(session, trigger_name)`
- `_delete_view_if_exists(session, view_name)`

Для сложных миграций можно комбинировать raw SQL и вызовы слоя Storage/DM.

---

## 4. Применение миграций

Команда `ra-apply-migration` выполняет upgrade схемы:

```bash
ra-apply-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test
```

Основные опции:

- `--path` / `-p` — путь к каталогу миграций.
- `--db-connection` — строка подключения к БД (попадает в `CONF.db.connection_url`).
- `--migration` / `-m` — целевая миграция; по умолчанию `HEAD`.
- `--dry-run` — прогон без реальных изменений.

Без `-m`:

- Вычисляется head-миграция (последняя автоматическая).
- Применяются все неприменённые автоматические миграции до неё.

С `-m X`:

- Применяются все неприменённые миграции, необходимые для достижения `X`.

---

## 5. Откат миграций

Команда `ra-rollback-migration` откатывает схему до указанной миграции:

```bash
ra-rollback-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test \
  --migration 0003-add-index
```

Опции:

- `--path` / `-p` — путь к миграциям.
- `--db-connection` — строка подключения к БД.
- `--migration` / `-m` — целевая миграция (обязательный параметр).
- `--dry-run` — прогон без фактических изменений.

Процесс отката:

- Сначала откатываются все миграции, зависящие от целевой.
- Затем вызывается `downgrade()` целевой миграции, и её запись помечается как `applied=False`.

Если миграция уже не применена, выводится предупреждение.

---

## 6. Переименование миграций в новый формат

`ra-rename-migrations` конвертирует существующие файлы в новый формат имён:

```bash
ra-rename-migrations --path examples/migrations/
```

Инструмент:

- Анализирует все миграции и вычисляет индекс для каждой.
- Формирует имена:
  - Автоматические: `0001-oldname-<hash>.py`
  - Ручные: `MANUAL-oldname-<hash>.py`
- Переименовывает файлы на диске.
- Обновляет зависимости внутри файлов миграций на новые имена.

---

## 7. Рекомендации

- Держите каталог миграций под системой контроля версий.
- Используйте осмысленные сообщения `--message` — они попадут в имена файлов.
- Автоматические миграции применяйте для типичных изменений схемы, ручные — только для особых случаев.
- Прогоняйте миграции в CI против тестовой БД перед обновлением production.
