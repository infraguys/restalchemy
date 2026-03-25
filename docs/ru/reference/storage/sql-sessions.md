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

# SQL-сессии и транзакции

Модуль: `restalchemy.storage.sql.sessions`

Модуль определяет классы сессий для PostgreSQL и MySQL, кэш запросов и вспомогательные функции для управления сессиями.

---

## SessionQueryCache

`SessionQueryCache` — кэш результатов запросов на уровне одной сессии.

- Строит хэш на основе SQL-выражения и параметров.
- Кэширует результаты `get_all()` и `query()`.
- Повторно использует результат при идентичном запросе в рамках сессии.

Используется внутри `PgSQLSession` и `MySQLSession`, когда включён флаг `cache=True`.

---

## PgSQLSession

`PgSQLSession` оборачивает соединение и курсор PostgreSQL:

- Получает соединения через `PgSQLEngine.get_connection()`.
- Использует `pg_rows.dict_row` для возврата строк в виде словарей.
- Предоставляет методы `execute()`, `execute_many()`, `commit()`, `rollback()`, `close()`.
- Реализует `batch_insert(models)` и `batch_delete(models)`:
  - Проверяет, что все модели одного типа.
  - Формирует пакетные операции через диалект `pgsql`.

Обычно управляется через:

- `engine.session_manager()` (из `AbstractEngine`), или
- `sessions.session_manager(engine, session=None)`.

---

## MySQLSession

`MySQLSession` аналогичен `PgSQLSession`, но:

- Использует MySQL-соединения из `MySQLEngine`.
- Работает с курсорами `mysql.connector` (`dictionary=True`).
- Использует диалект `mysql` (`MySQLInsert`, `MySQLBatchDelete` и др.).

Также поддерживает:

- `batch_insert(models)` и `batch_delete(models)`.
- Преобразование типичных ошибок (deadlock, нарушения целостности) в исключения слоя хранения.

---

## session_manager

Есть два родственных механизма управления сессиями:

1. `engines.AbstractEngine.session_manager()`
2. `sessions.session_manager(engine, session=None)`

`engine.session_manager()`:

- Если сессия не передана:
  - Создаёт новую сессию через `engine.get_session()`.
  - Вызывает `commit()` при успешном завершении блока.
  - Вызывает `rollback()` при исключении.
  - Закрывает сессию после выхода из блока.
- Если сессия передана, просто yield-ит её без дополнительной логики.

Пример:

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    foo = FooModel(foo_field1=42)
    foo.save(session=session)
```

`sessions.session_manager(engine, session=None)` реализует похожую логику на уровне модуля `sessions`.

---

## SessionThreadStorage

`SessionThreadStorage` — потокобезопасное хранилище сессий:

- Хранит одну сессию на поток.
- Методы:
  - `get_session()` — вернуть сессию или бросить `SessionNotFound`.
  - `store_session(session)` — сохранить сессию, бросить `SessionConflict`, если уже есть.
  - `remove_session()` / `pop_session()` — удалить или получить+удалить сессию.

Движки используют `SessionThreadStorage` как хранилище сессий, чтобы:

- Одна и та же сессия могла использоваться несколькими операциями в пределах одного потока.
- Код верхнего уровня мог интегрировать сессии RESTAlchemy в существующую систему управления транзакциями.
