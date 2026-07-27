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

# API basic CRUD

В этом руководстве показано, как построить простой REST API на основе API-слоя RESTAlchemy.

Мы:

- Опишем DM-модели.
- Реализуем контроллеры.
- Опишем маршруты.
- Соберём WSGI-приложение.
- Проверим API с помощью `curl`.

Пример основан на `examples/restapi_foo_bar_service.py`.

---

## 1. DM-модели

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

- `FooModel` и `BarModel` — чистые DM-модели (хранения здесь нет, только память).
- `BarModel.foo` описывает связь с `FooModel`.

---

## 2. In-memory-хранилище

Для простоты используем словари Python:

```python
foo_storage = {}
bar_storage = {}
```

В реальном приложении вместо этого использовались бы модели с SQL-хранилищем (`SQLStorableMixin`), но API-слой при этом выглядит так же.

---

## 3. Контроллеры

Контроллеры связывают HTTP-методы с кодом на Python.

```python
from restalchemy.api import controllers, resources


class FooController(controllers.Controller):
    """Обработчик для /foos/."""

    __resource__ = resources.ResourceByRAModel(FooModel, process_filters=True)

    def create(self, foo_field1, foo_field2):
        foo = self.model(foo_field1=foo_field1, foo_field2=foo_field2)
        foo_storage[str(foo.get_id())] = foo
        return foo

    def get(self, uuid):
        return foo_storage[uuid]

    def filter(self, filters, order_by=None):
        return foo_storage.values()


bar_resource = resources.ResourceByRAModel(BarModel, process_filters=True)


class BarController1(controllers.Controller):
    """Обработчик для /foo/<uuid>/bars/."""

    __resource__ = bar_resource

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.get_id())] = bar
        return bar


class BarController2(controllers.Controller):
    """Обработчик для /bars/<uuid>."""

    __resource__ = bar_resource

    def get(self, uuid):
        return bar_storage[uuid]

    def delete(self, uuid):
        del bar_storage[uuid]
```

Ключевые идеи:

- `__resource__` указывает контроллеру, с какой DM-моделью/ресурсом он работает.
- `create/get/filter/delete` — RA-методы, которые маршруты отображают на HTTP.
- `process_filters=True` у ресурса включает автоматический разбор query-параметров.

---

## 4. Маршруты

Маршруты сопоставляют URL и HTTP-методы методам контроллеров.

```python
from restalchemy.api import routes


class BarRoute1(routes.Route):
    __controller__ = BarController1
    __allow_methods__ = [routes.CREATE]


class BarRoute2(routes.Route):
    __controller__ = BarController2
    __allow_methods__ = [routes.GET, routes.DELETE]


class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.FILTER, routes.CREATE, routes.GET]

    bars = routes.route(BarRoute1, resource_route=True)


class V1Route(routes.Route):
    __controller__ = controllers.RoutesListController
    __allow_methods__ = [routes.FILTER]

    foos = routes.route(FooRoute)
    bars = routes.route(BarRoute2)


class UserApiApp(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


setattr(UserApiApp, "v1", routes.route(V1Route))
```

- `FooRoute` обслуживает `/v1/foos/` и `/v1/foos/<uuid>`.
- `BarRoute1` обслуживает `/v1/foos/<uuid>/bars/`.
- `BarRoute2` обслуживает `/v1/bars/<uuid>`.
- `V1Route` и `UserApiApp` группируют эти маршруты под `/v1/` и корнем `/`.

---

## 5. WSGI-приложение

```python
from wsgiref.simple_server import make_server
from restalchemy.api import applications, middlewares


HOST = "0.0.0.0"
PORT = 8000


def get_user_api_application():
    return UserApiApp


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.WSGIApp(get_user_api_application()),
        [],
    )


def main():
    server = make_server(HOST, PORT, build_wsgi_application())
    try:
        print("Serve forever on %s:%s" % (HOST, PORT))
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()
```

- `WSGIApp` оборачивает корневой маршрут и строит `ResourceMap`.
- `middlewares.attach_middlewares` позволяет добавить логирование, обработку ошибок и т. п.

---

## 6. Проверка API

Предполагая, что сервер запущен на `http://127.0.0.1:8000`.

### Список маршрутов верхнего уровня

```bash
curl http://127.0.0.1:8000/
```

### Создать Foo

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/" \
  -H "Content-Type: application/json" \
  -d '{"foo_field1": 10, "foo_field2": "bar"}'
```

### Получить список всех Foo

```bash
curl "http://127.0.0.1:8000/v1/foos/"
```

### Получить Foo по UUID

```bash
curl "http://127.0.0.1:8000/v1/foos/<uuid>"
```

### Создать Bar для конкретного Foo

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/<uuid>/bars/" \
  -H "Content-Type: application/json" \
  -d '{"bar_field1": "test"}'
```

### Получить Bar по UUID

```bash
curl "http://127.0.0.1:8000/v1/bars/<uuid>"
```

### Удалить Bar по UUID

```bash
curl -X DELETE "http://127.0.0.1:8000/v1/bars/<uuid>"
```

---

## Итоги

- DM-модели описывают ваши данные.
- Контроллеры инкапсулируют бизнес-логику RA-методов (FILTER/CREATE/GET/UPDATE/DELETE).
- Маршруты сопоставляют HTTP-пути и методы контроллерам и ресурсам.
- `WSGIApp` связывает всё это в WSGI-приложение.

Этот подход масштабируется от простых in-memory-примеров до продуктивных конфигураций с SQL-хранилищем и OpenAPI.
