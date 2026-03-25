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

# Справочник по Storage

В этом разделе описывается слой хранения (Storage) в RESTAlchemy.

Основной пользовательский код находится в `restalchemy.storage.sql.*` и используется совместно с DM-моделями и API-слоем.

---

## Модули

- `restalchemy.storage.base`
  - Абстрактные интерфейсы для сохраняемых моделей и коллекций.
- `restalchemy.storage.exceptions`
  - Исключения, генерируемые слоем хранения.
- `restalchemy.storage.sql.engines`
  - Фабрика SQL-движков и конкретные реализации для MySQL и PostgreSQL.
- `restalchemy.storage.sql.sessions`
  - Сессии БД, вспомогательные функции для транзакций и кэш запросов.
- `restalchemy.storage.sql.orm`
  - ORM-подобные mixin-ы и `ObjectCollection`, используемые DM-моделями.
- `restalchemy.storage.sql.tables`
  - Абстракция таблиц, используемая ORM и диалектами.
- `restalchemy.storage.sql.dialect.*`
  - Диалект-специфичные построители запросов.

---

## Точки входа для типичного использования

Для большинства приложений достаточно:

1. Настроить движок:

   ```python
   from restalchemy.storage.sql import engines

   engines.engine_factory.configure_factory(
       db_url="mysql://user:password@127.0.0.1:3306/test",
   )
   ```

2. Описать DM-модели, наследующие `orm.SQLStorableMixin`, и задать `__tablename__`.

3. Использовать:

   - `Model.objects.get_all()` / `Model.objects.get_one()` для чтения.
   - `.save()` и `.delete()` на экземплярах моделей для записи.

Подробности по компонентам в отдельных файлах:

- [SQL-движки](sql-engines.md)
- [SQL ORM-mixin-ы и коллекции](sql-orm.md)
- [SQL-сессии и транзакции](sql-sessions.md)
