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

# Getting started

This guide walks you through building a tiny REST service with:

- An in-memory data store (no database required).
- A single DM model.
- A minimal API layer (controller + route).
- A WSGI application.

After completing this guide you will have a working HTTP API listening on `http://127.0.0.1:8000/`.

---

## 1. Project layout

Create a new file, for example:

```text
myservice/
  app.py
```

All code below goes into `app.py`.

---

## 2. Define a simple DM model

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

`FooModel` is a DM model with:

- An auto-generated UUID as primary key (inherited from `ModelWithUUID`).
- A single integer field `value`.

---

## 3. In-memory storage

For quick experiments we use a simple Python dictionary as storage:

```python
FOO_STORAGE = {}
```

---

## 4. Define a controller

Controllers implement the business logic for HTTP methods. We will support:

- `CREATE`
- `GET`
- `FILTER` (list all foos)

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

## 5. Define routes

Routes map URLs and HTTP methods to controllers.

```python
class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.CREATE, routes.GET, routes.FILTER]


class ApiRoot(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]

    foos = routes.route(FooRoute)
```

Now:

- `GET /` will list available top-level routes.
- `POST /foos/` will create a new `FooModel`.
- `GET /foos/<uuid>` will fetch a specific `FooModel`.
- `GET /foos/` will list all foos.

---

## 6. Build the WSGI application

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

## 7. Run the development server

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

Run:

```bash
python app.py
```

You should see:

```text
Serve forever on 127.0.0.1:8000
```

---

## 8. Try the API

Create a new `Foo`:

```bash
curl -X POST "http://127.0.0.1:8000/foos/" \
  -H "Content-Type: application/json" \
  -d '{"value": 42}'
```

You should get a JSON response with a generated UUID.

List all foos:

```bash
curl "http://127.0.0.1:8000/foos/"
```

Get a single foo (replace `<uuid>` with the one you received):

```bash
curl "http://127.0.0.1:8000/foos/<uuid>"
```

---

## 9. Next steps

After this minimal in-memory service, you can:

- Move to SQL storage: see `concepts/data-model.md`, `concepts/storage-layer.md` and the DM + SQL how-to.
- Explore the full example: `examples/restapi_foo_bar_service.py`.
- Learn about filters, relationships and more advanced scenarios in the how-to guides.
