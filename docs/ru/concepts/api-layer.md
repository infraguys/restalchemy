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

# API layer

API-слой в RESTAlchemy связывает HTTP-запросы с DM-моделями и слоем хранения.

Он отвечает за:

- Маршрутизацию HTTP-путей и методов к контроллерам.
- Связку контроллеров с ресурсами поверх DM-моделей.
- Сериализацию и десериализацию тел запросов/ответов.
- Применение прав на поля и фильтров.
- (Опционально) публикацию спецификации OpenAPI.

---

## Основные составляющие

### 1. Приложения

Модуль: `restalchemy.api.applications`

- `WSGIApp` / `Application`:
  - Точка входа для WSGI-сервера.
  - Принимает корневой класс маршрута (подкласс `routes.Route`).
  - Строит карту ресурсов через `routes.Route.build_resource_map()` и `resources.ResourceMap.set_resource_map()`.
  - Для каждого запроса:
    - Создаёт `RequestContext`.
    - Вызывает `main_route(req).do()`.

- `OpenApiApplication(WSGIApp)`:
  - Расширяет `WSGIApp` поддержкой `openapi_engine`.
  - Используется при публикации OpenAPI.

### 2. Маршруты

Модуль: `restalchemy.api.routes`

- `BaseRoute`:
  - Знает, какой контроллер обрабатывает маршрут (`__controller__`).
  - Хранит список разрешённых методов (`__allow_methods__`).
  - Реализует `do()` для обработки запроса.

- `Route(BaseRoute)`:
  - Представляет коллекционные и ресурсные маршруты.
  - Определяет RA-метод (`FILTER/CREATE/GET/UPDATE/DELETE`) на основе HTTP-метода.
  - Делегирует вызов методам контроллера (`do_collection`, `do_resource`, вложенные маршруты, actions).
  - Умеет генерировать OpenAPI-спецификацию.

- `Action(BaseRoute)`:
  - Обрабатывает маршруты вида `/actions/` для операций над конкретными ресурсами.

- Вспомогательные функции:
  - `route(route_class, resource_route=False)` — помечает вложенный маршрут как коллекционный или ресурсный.
  - `action(action_class, invoke=False)` — управляет поведением action (`.../invoke`).

### 3. Контроллеры

Модуль: `restalchemy.api.controllers`

- `Controller`:
  - Базовый контроллер, работающий с ресурсом (`__resource__`).
  - Управляет packer-ами для формирования ответа.
  - Реализует `process_result()` для сборки `webob.Response`.

- `BaseResourceController` и его вариации:
  - Реализуют `create`, `get`, `filter`, `update`, `delete` для DM-моделей.
  - Поддерживают сортировку, фильтрацию, пагинацию, кастомные фильтры.

- `RoutesListController`, `RootController`:
  - Используются для выдачи списка доступных маршрутов (`/`, `/v1/`).

- `OpenApiSpecificationController`:
  - Отдаёт спецификацию OpenAPI, используя настроенный `openapi_engine`.

### 4. Ресурсы

Модуль: `restalchemy.api.resources`

- `ResourceMap`:
  - Глобальное соответствие типов DM-моделей ресурсам и URL-локаторам.
  - Используется для построения заголовков `Location` и для поиска ресурса по произвольному URI.

- `ResourceByRAModel`:
  - Описывает, как DM-модель отображается в API:
    - какие поля публичные,
    - как конвертировать свойства модели в поля API и обратно.
  - Используется packer-ами и контроллерами при обработке запросов.

### 5. Packer-ы

Модуль: `restalchemy.api.packers`

- `BaseResourcePacker`:
  - Сериализует ресурсы в простые типы (`dict`, `list`, скаляры).
  - Десериализует тела запросов в значения полей модели.

- `JSONPacker`, `JSONPackerIncludeNullFields`:
  - Конвертируют между JSON и данными ресурса.

- `MultipartPacker`:
  - Обрабатывает `multipart/form-data` (например, загрузку файлов).

### 6. Контекс и права на поля

- `contexts.RequestContext`:
  - Крепится к запросу как `req.api_context`.
  - Хранит активный RA-метод (`FILTER/CREATE/...`).
  - Предоставляет доступ к параметрам и фильтрующим параметрам.

- Модуль `field_permissions`:
  - `UniversalPermissions`, `FieldsPermissions`, `FieldsPermissionsByRole`.
  - Управляют видимостью (`HIDDEN`), доступностью только для чтения (`RO`) и чтение/запись (`RW`) полей в зависимости от метода и роли.

### 7. Actions

Модуль: `restalchemy.api.actions`

- `ActionHandler` и декораторы:
  - `@actions.get`, `@actions.post`, `@actions.put`.
  - Реализуют поведение методов для actions над ресурсами.

В сочетании с `routes.Action` и `routes.action` дают паттерн для эндпоинтов вида `/v1/files/<id>/actions/download`.

---

## Поток обработки запроса

1. **HTTP-запрос приходит** на WSGI-сервер.
2. Вызывается `WSGIApp.__call__`:
   - создаётся `RequestContext` и привязывается к `req.api_context`;
   - вызывается `main_route(req).do()`.
3. **Route** (`Route` / `Action`) анализирует `req.path_info` и `req.method`:
   - разрешает вложенные маршруты и actions;
   - определяет RA-метод (FILTER/CREATE/GET/UPDATE/DELETE или action);
   - создаёт контроллер и передаёт ему управление.
4. **Контроллер**:
   - разбирает фильтры, сортировку и пагинацию из `RequestContext`;
   - взаимодействует с ресурсами и DM-моделями (и опосредованно со Storage);
   - через `process_result()` и packer формирует `webob.Response`.
5. **Ответ** возвращается клиенту.

Интеграция с OpenAPI использует те же маршруты, контроллеры и ресурсы для построения спецификации, которую отдаёт `OpenApiSpecificationController` через `OpenApiApplication`.
