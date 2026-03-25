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

# Nested resources и actions

В этом руководстве показано, как:

- реализовать вложенные ресурсы (например, `/foos/<uuid>/bars/`),
- реализовать actions над ресурсами (например, `/v1/files/<id>/actions/download`).

Руководство опирается на базовый пример CRUD и использует идеи из `examples/restapi_foo_bar_service.py` и `examples/openapi_app.py`.

---

## 1. Nested resources

Вложенные ресурсы представляют иерархические отношения, например:

- родительский ресурс: `FooModel` по пути `/v1/foos/<uuid>`.
- вложенная коллекция: `BarModel` по пути `/v1/foos/<uuid>/bars/`.

### 1.1. DM-модели

Как в базовом примере CRUD:

```python
class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

### 1.2. Вложенный контроллер

Вы можете использовать `BaseNestedResourceController` для работы с вложенными ресурсами или реализовать контроллер вручную.

Пример с явной обработкой родителя (упрощённо):

```python
class BarController1(controllers.Controller):
    """Handle /v1/foos/<uuid>/bars/."""

    __resource__ = resources.ResourceByRAModel(BarModel, process_filters=True)

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.get_id())] = bar
        return bar

    def filter(self, filters, parent_resource, order_by=None):
        # Add parent filter to restrict bars to this foo
        return [
            bar for bar in bar_storage.values() if bar.foo == parent_resource
        ]
```

В качестве альтернативы, `BaseNestedResourceController` предоставляет встроенные паттерны для работы с `parent_resource`.

### 1.3. Вложенный роут

```python
class BarRoute1(routes.Route):
    __controller__ = BarController1
    __allow_methods__ = [routes.CREATE, routes.FILTER]


class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.FILTER, routes.CREATE, routes.GET]

    bars = routes.route(BarRoute1, resource_route=True)
```

- `resource_route=True` говорит RA, что `BarRoute1` работает с ресурсами, вложенными под конкретную родительскую инстанцию.
- Для `/v1/foos/<foo_uuid>/bars/` RA резолвит родительский `FooModel` и передаёт его в контроллер как `parent_resource`.

---

## 2. Actions над ресурсами

Actions представляют операции, которые не являются чистым CRUD для основного ресурса. Типичные примеры:

- `/v1/files/<id>/actions/download` — скачать файл.
- `/v1/objects/<id>/actions/some_business_operation`.

### 2.1. Определение action через ActionHandler

Модуль: `restalchemy.api.actions`

```python
from restalchemy.api import actions, constants
from restalchemy.api import controllers, resources


class FileModel(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)


class FilesController(controllers.Controller):
    __resource__ = resources.ResourceByRAModel(
        model_class=FileModel,
        process_filters=True,
        convert_underscore=False,
    )

    @actions.get
    def download(self, resource, **kwargs):
        # Suppose resource represents a file description and you
        # want to return binary content.
        data = resource.download_file()  # user-implemented method
        headers = {
            "Content-Type": constants.CONTENT_TYPE_OCTET_STREAM,
            "Content-Disposition": f'attachment; filename="{resource.name}"',
        }
        return data, 200, headers
```

- `@actions.get` оборачивает `download` в `ActionHandler`.
- Метод контроллера получает `self` как `controller`, а `resource` — как текущий экземпляр DM.
- Для построения ответа используется `controller.process_result()` (через `ActionHandler.do_*`).

### 2.2. Определение Action route

```python
from restalchemy.api import routes


class FileDownloadAction(routes.Action):
    """Handler for /v1/files/<id>/actions/download endpoint."""

    __controller__ = FilesController
```

Затем вы подключаете этот action к resource route:

```python
class FilesRoute(routes.Route):
    """Handler for /v1/files/<id> endpoint."""

    __controller__ = FilesController
    __allow_methods__ = [
        routes.CREATE,
        routes.DELETE,
        routes.FILTER,
        routes.GET,
        routes.UPDATE,
    ]

    download = routes.action(FileDownloadAction, invoke=True)
```

- `routes.action(FileDownloadAction, invoke=True)` означает:
  - action доступен по пути `/v1/files/<id>/actions/download/invoke`.
  - HTTP-методы `GET/POST/PUT` маппятся на `do_get/do_post/do_put` в `ActionHandler`.

### 2.3. Request/response flow для actions

Для URL вида `/v1/files/<id>/actions/download/invoke`:

1. `Route.do()` распознаёт сегмент `actions` в пути.
2. Загружает ресурс по `<id>` через контроллер.
3. Резолвит action (`download`).
4. Инстанцирует `FileDownloadAction` с request.
5. Вызывает `Action.do(resource=resource, **kwargs)`.
6. `Action` использует `ActionHandler`, чтобы вызвать правильный `do_*` метод обёрнутой функции.

---

## 3. Комбинация nested resources и actions

Actions можно использовать и на вложенных ресурсах:

- Например, `/v1/foos/<foo_id>/bars/<bar_id>/actions/archive`.

В этом случае:

- дерево роутов описывает вложенные пути до `BarRoute`;
- action под `BarRoute` может работать с вложенной инстанцией `BarModel`.

Паттерн тот же, что и для top-level ресурсов; меняется только routing path.

---

## Резюме

- Nested resources выражаются через вложенные `Route` классы и `resource_route=True`.
- Контроллеры могут использовать `parent_resource` (или `BaseNestedResourceController`) для реализации логики, завязанной на родительскую DM-инстанцию.
- Actions реализуются через декораторы `ActionHandler` и `routes.Action`/`routes.action`, что даёт чистый способ описывать не-CRUD операции над ресурсами.
