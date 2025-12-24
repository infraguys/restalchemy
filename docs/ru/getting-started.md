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

# Быстрый старт

В этом руководстве вы соберёте небольшой REST-сервис, который:

- Использует in-memory-хранилище (без БД).
- Использует одну DM-модель.
- Использует минимальный API-слой (контроллер + роут).
- Запускается как WSGI-приложение.

В конце у вас будет HTTP API на `http://127.0.0.1:8000/`.

---

## 1. Структура проекта

Создайте директорию и файл:

```text
myservice/
  app.py
```

Весь код ниже размещается в `app.py`.

---

## 2. Простая DM-модель

```python
from wsgiref.simple_server import make_server

from restalchemy.api import applications
from restalchemy.api import controllers
from restalchemy.api import middlewares
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types


# Simple data model for a "Foo" resource
class FooModel(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)
```

`FooModel` — DM-модель с:

- Автоматически генерируемым UUID (унаследовано от `ModelWithUUID`).
- Одним целочисленным полем `value`.

---

## 3. In-memory-хранилище

Для экспериментов достаточно словаря:

```python
FOO_STORAGE = {}
```

---

## 4. Контроллер

Контроллер реализует логику для HTTP-методов `CREATE`, `GET` и `FILTER`:

```python
class FooController(controllers.Controller):
    __resource__ = resources.ResourceByRAModel(FooModel, process_filters=True)

    def create(self, value):
        foo = self.model(value=value)
        FOO_STORAGE[str(foo.get_id())] = foo
        return foo

    def get(self, uuid):
        return FOO_STORAGE[uuid]

    def filter(self, filters, order_by=None):
        return FOO_STORAGE.values()
```

---

## 5. Маршруты

Маршруты сопоставляют URL и методы контроллерам:

```python
class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.CREATE, routes.GET, routes.FILTER]


class ApiRoot(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]

    foos = routes.route(FooRoute)
```

Теперь:

- `GET /` — корневой список маршрутов.
- `POST /foos/` — создание нового `FooModel`.
- `GET /foos/<uuid>` — получение одного объекта.
- `GET /foos/` — список всех объектов.

---

## 6. WSGI-приложение

```python
def get_user_api_application():
    return ApiRoot


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.WSGIApp(get_user_api_application()),
        [],
    )
```

---

## 7. Запуск сервера

```python
HOST = "127.0.0.1"
PORT = 8000


def main():
    server = make_server(HOST, PORT, build_wsgi_application())

    try:
        print(f"Serve forever on {HOST}:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()
```

Запуск:

```bash
python app.py
```

---

## 8. Проверка API

Создание `Foo`:

```bash
curl -X POST "http://127.0.0.1:8000/foos/" \
  -H "Content-Type: application/json" \
  -d '{"value": 42}'
```

Список всех:

```bash
curl "http://127.0.0.1:8000/foos/"
```

Получение одного объекта (подставьте `<uuid>`):

```bash
curl "http://127.0.0.1:8000/foos/<uuid>"
```

---

## 9. Дальнейшие шаги

После минимального in-memory-сервиса можно:

- Перейти к SQL-хранилищу (см. `concepts/data-model.md`, `concepts/storage-layer.md` и how-to по DM+SQL).
- Посмотреть полный пример `examples/restapi_foo_bar_service.py`.
- Изучить фильтры, связи и другие сценарии в how-to-разделах.
