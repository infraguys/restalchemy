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

# SQL-движки

Модуль: `restalchemy.storage.sql.engines`

Модуль содержит фабрику движков и конкретные реализации SQL-движков для MySQL и PostgreSQL.

---

## AbstractEngine

`AbstractEngine` описывает общее поведение всех SQL-движков:

- Парсит URL подключения к БД.
- Предоставляет имя БД, хост, порт, логин и пароль.
- Хранит диалект SQL (`mysql.MySQLDialect` или `pgsql.PgSQLDialect`).
- Предоставляет контекстный менеджер `session_manager()`.

Ключевые члены:

- `URL_SCHEMA` (абстрактное свойство): ожидаемая схема URL (`"mysql"`, `"postgresql"`).
- `DEFAULT_PORT` (абстрактное свойство): порт по умолчанию.
- `db_name`, `db_username`, `db_password`, `db_host`, `db_port`.
- `dialect`: объект диалекта.
- `query_cache`: признак включённого кэша запросов.
- `get_connection()`: получение соединения (реализуется в подклассах).
- `get_session()`: получение сессии (реализуется в подклассах).
- `session_manager(session=None)`: контекстный менеджер для управления транзакцией и жизненным циклом сессии.

---

## PostgreSQL-движок

### `PgSQLEngine`

- `URL_SCHEMA = "postgresql"`.
- Порт по умолчанию берётся из `RA_POSTGRESQL_DB_PORT`.
- Использует пул `psycopg_pool.ConnectionPool`.
- Диалект: `pgsql.PgSQLDialect()`.
- Тип сессии: `sessions.PgSQLSession`.

Конструктор:

```python
PgSQLEngine(db_url, config=None, query_cache=False)
```

Методы:

- `get_session()`: возвращает `PgSQLSession(engine=self)`.
- `get_connection()`: берёт соединение из пула.
- `close_connection(conn)`: возвращает соединение в пул.

---

## MySQL-движок

### `MySQLEngine`

- `URL_SCHEMA = "mysql"`.
- Порт по умолчанию из `RA_MYSQL_DB_PORT`.
- Использует `mysql.connector.pooling.MySQLConnectionPool`.
- Диалект: `mysql.MySQLDialect()`.
- Тип сессии: `sessions.MySQLSession`.

Конструктор:

```python
MySQLEngine(db_url, config=None, query_cache=False)
```

Методы:

- `get_connection()`: возвращает соединение из пула.
- `get_session()`: возвращает `MySQLSession(engine=self)`.

---

## EngineFactory и engine_factory

### `EngineFactory`

Синглтон, отвечающий за конфигурацию и хранение экземпляров движков.

Основные методы:

- `configure_factory(db_url, config=None, query_cache=False, name="default")`
  - Создаёт экземпляр движка на основе `db_url` и сохраняет его под именем `name`.
- `configure_postgresql_factory(conf, section, name)`
  - Упрощённая настройка PostgreSQL из конфигурационного объекта.
- `configure_mysql_factory(conf, section, name)`
  - Упрощённая настройка MySQL.
- `get_engine(name="default")`
  - Возвращает настроенный движок.
- `destroy_engine(name="default")` / `destroy_all_engines()`
  - Удаляют один или все движки.

На уровне модуля определён синглтон:

```python
engine_factory = EngineFactory()
```

Обычно используется так:

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(db_url="mysql://...")
engine = engines.engine_factory.get_engine()
```

---

## DBConnectionUrl

`DBConnectionUrl` — небольшой вспомогательный класс для парсинга и безопасного вывода URL подключения к БД.

- Хранит распарсенный URL.
- Свойство `url` возвращает полный URL.
- `__repr__` скрывает пароль, подставляя `:<censored>@`.

Полезен в основном для логирования и отладки.
