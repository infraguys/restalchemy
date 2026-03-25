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

# Слой хранения (Storage layer)

Слой хранения в RESTAlchemy отвечает за сохранение DM-моделей в базе данных и их последующее чтение.

Он построен как отдельный слой поверх DM (Data Model) и под API-слоем.

---

## Обзор модулей

Основные модули, относящиеся к SQL-хранилищу:

- `restalchemy.storage.base`
  - Абстрактные интерфейсы для сохраняемых моделей и коллекций.
- `restalchemy.storage.exceptions`
  - Исключения уровня хранения.
- `restalchemy.storage.sql.engines`
  - Фабрика движков и реализации движков для MySQL/PostgreSQL.
- `restalchemy.storage.sql.sessions`
  - Сессии БД, транзакции и кэш запросов на уровне сессии.
- `restalchemy.storage.sql.orm`
  - ORM-подобные mixin-ы и коллекции (`SQLStorableMixin`, `ObjectCollection`).
- `restalchemy.storage.sql.tables`
  - Абстракция таблиц, используемая ORM и диалектами.
- `restalchemy.storage.sql.dialect.*`
  - Диалект-специфичные построители запросов для MySQL и PostgreSQL.

Обычно вы взаимодействуете только с:

- DM-моделями + `orm.SQLStorableMixin`;
- `engines.engine_factory.configure_factory()` для настройки движка;
- коллекцией `Model.objects` и методами `save()`/`delete()` у экземпляров.

---

## Архитектура на высоком уровне

### 1. DM-модель

Вы описываете модель, наследуясь одновременно от:

- `models.ModelWithUUID` (или другого базового `Model*`), и
- `orm.SQLStorableMixin`.

Упрощённый пример (по мотивам `examples/dm_mysql_storage.py`):

```python
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "bars"
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

### 2. Движок и сессии

Модуль `restalchemy.storage.sql.engines` содержит `engine_factory`, который управляет SQL-движками.

Типичная конфигурация:

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/mydb",
)
```

Ключевые идеи:

- **Engine** парсит `db_url`, настраивает пул соединений и диалект.
- **Session** (`PgSQLSession` / `MySQLSession`) создаётся движком и выполняет запросы.
- `session_manager(engine, session=None)` из `sessions.py` оборачивает работу с сессией в транзакцию.

### 3. ORM-mixin и коллекции

`restalchemy.storage.sql.orm` предоставляет:

- `SQLStorableMixin` — mixin для DM-моделей, хранимых в SQL.
- `ObjectCollection` — коллекция объектов, доступная как `Model.objects`.

Ответственность:

- **`SQLStorableMixin`**:
  - Связывает DM-модель с таблицей через `__tablename__` и `get_table()`.
  - Реализует `insert()`, `save()`, `update()`, `delete()`.
  - Конвертирует свойства DM в значения, пригодные для хранения, и обратно.

- **`ObjectCollection`**:
  - Предоставляет методы `get_all()`, `get_one()`, `get_one_or_none()`, `query()`, `count()`.
  - Использует фильтры (`restalchemy.dm.filters`) для описания WHERE-условий.

### 4. Диалекты и таблицы

Модули диалектов (`restalchemy.storage.sql.dialect.*`) и `tables.SQLTable` — внутренние помощники, которые:

- Строят SQL-запросы (SELECT/INSERT/UPDATE/DELETE).
- Подставляют параметры.
- Выполняют запросы через сессии.

Как правило, вам не нужно обращаться к ним напрямую — ими управляют модели и коллекции.

---

## Жизненный цикл модели с SQL-хранилищем

1. **Определение модели**
   - Наследуемся от `ModelWithUUID` и `SQLStorableMixin`.
   - Задаём `__tablename__`.
   - Описываем поля и связи через свойства DM.

2. **Настройка движка**
   - Один раз при старте приложения вызываем `engine_factory.configure_factory(db_url=...)`.

3. **Создание таблиц / миграции**
   - Используем инструменты миграций (`ra-new-migration`, `ra-apply-migration`) для создания/обновления схемы БД.

4. **CRUD-операции**
   - Создаём экземпляры моделей и вызываем `.save()`.
   - Используем `Model.objects.get_all()` / `.get_one(filters=...)` для чтения.
   - Вызываем `.delete()` для удаления.

5. **Фильтры и сложные запросы**
   - Строим фильтры через `restalchemy.dm.filters` и передаём их в `objects.get_all()` / `objects.get_one()`.

6. **Транзакции и сессии (по необходимости)**
   - Оборачиваем группы операций в явный `session_manager()`, когда нужен точный контроль над транзакциями.

Все эти шаги показаны в DM+SQL how-to и в примерах `examples/dm_mysql_storage.py` и `examples/dm_pg_storage.py`.
