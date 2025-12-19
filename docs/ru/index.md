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

# RESTAlchemy

RESTAlchemy — это Python-инструментарий для построения HTTP REST API поверх гибкой модели данных и абстракции хранилища.

Он объединяет:

- Слой **Data Model (DM)** для описания доменных моделей и валидации.
- Слой **Storage** для работы с хранилищами (например, SQL-БД).
- Слой **API** для публикации моделей как REST-ресурсов.
- Опционально — поддержку **OpenAPI** для самодокументируемых API.

Документация доступна на четырёх языках:

- Английский (`docs/en`)
- Русский (`docs/ru`)
- Немецкий (`docs/de`)
- Китайский (`docs/zh`)

Структура файлов и разделов во всех языках одинакова.

---

## Ключевые концепции

### Data Model (DM)

DM отвечает за:

- Объявление моделей и полей.
- Валидацию значений и типов.
- Описание связей между моделями.

Вы описываете Python-классы, наследуясь от базовых классов DM (например, `ModelWithUUID`), и используете `properties` и `types` для задания полей.

### Storage

Слой хранилища предоставляет:

- Абстракцию над SQL-движками (MySQL, PostgreSQL и др.).
- Сессии и транзакции.
- Утилиты для запросов и фильтрации.

Вы можете начать без постоянного хранилища (только in-memory) и позже подключить SQL-хранилище.

### API

Слой API включает:

- Контроллеры, реализующие бизнес-логику.
- Ресурсы, описывающие, как DM-модели доступны по HTTP.
- Маршруты, сопоставляющие URL и HTTP-методы контроллерам.
- Middleware и WSGI-приложения.

Можно начать с маленького сервиса с хранением в памяти и затем постепенно добавить DM и Storage для продакшена.

### OpenAPI (опционально)

Интеграция с OpenAPI позволяет:

- Автоматически генерировать спецификации OpenAPI по контроллерам и маршрутам.
- Отдавать спецификации из вашего API.
- Интегрироваться с Swagger UI и генераторами клиентов.

---

## Когда стоит использовать RESTAlchemy?

RESTAlchemy полезен, если:

- **Нужно** чётко разделить:
  - доменные модели (DM),
  - детали хранилища,
  - HTTP-API,  
  но не хочется использовать тяжёлый фреймворк.
- **Важно**, чтобы модель данных была типизированной и валидируемой.
- **Нужно** быстро публиковать модели как REST-ресурсы с минимумом шаблонного кода.
- **Важны** миграции и эволюция схемы БД.

---

## Быстрая навигация

Рекомендуемый порядок чтения для новых пользователей:

1. [Установка](installation.md)
2. [Быстрый старт](getting-started.md) — построение небольшого REST-сервиса в памяти.
3. Концепции:
   - [Модель данных](concepts/data-model.md)
   - [API-слой](concepts/api-layer.md)
   - [Слой хранилища](concepts/storage-layer.md)
4. How-to:
   - Базовый CRUD
   - Фильтрация, сортировка, пагинация
   - Связи между моделями
5. Reference:
   - `restalchemy.api.*`
   - `restalchemy.dm.*`
   - `restalchemy.storage.*`

После чтения только:

- `installation.md`
- `getting-started.md`

вы уже сможете собрать работающий сервис.

---

## Примеры

Реальные примеры кода находятся в каталоге `examples/` репозитория. В частности:

- `examples/restapi_foo_bar_service.py`  
  Простой REST-сервис с in-memory-хранением.
- `examples/dm_mysql_storage.py`  
  Пример работы модели данных с MySQL-хранилищем.
- `examples/openapi_app.py`  
  Пример API со спецификацией OpenAPI.
