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

This guide shows how to build a simple REST API using RESTAlchemy's API layer.

We will:

- Define DM models.
- Define controllers.
- Define routes.
- Build a WSGI application.
- Call the API with `curl`.

The example is based on `examples/restapi_foo_bar_service.py`.

---

## 1. DM models

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

- `FooModel` and `BarModel` are pure DM models (no storage here, in-memory only).
- `BarModel.foo` expresses a relationship to `FooModel`.

---

## 2. In-memory storage

For simplicity we use Python dictionaries:

```python
foo_storage = {}
bar_storage = {}
```

In a real application you would use SQL storage models (`SQLStorableMixin`) instead, but the API layer is the same.

---

## 3. Controllers

Controllers connect HTTP methods to Python code.

```python
from restalchemy.api import controllers, resources


class FooController(controllers.Controller):
    """Handle /foos/ endpoints."""

    __resource__ = resources.ResourceByRAModel(FooModel, process_filters=True)

    def create(self, foo_field1, foo_field2):
        foo = self.model(foo_field1=foo_field1, foo_field2=foo_field2)
        foo_storage[str(foo.get_id())] = foo
        return foo

    def get(self, uuid):
        return foo_storage[uuid]

    def filter(self, filters, order_by=None):
        # Simple implementation: ignore filters and order_by
        return foo_storage.values()


bar_resource = resources.ResourceByRAModel(BarModel, process_filters=True)


class BarController1(controllers.Controller):
    """Handle /foo/<uuid>/bars/ endpoints."""

    __resource__ = bar_resource

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.get_id())] = bar
        return bar


class BarController2(controllers.Controller):
    """Handle /bars/<uuid> endpoints."""

    __resource__ = bar_resource

    def get(self, uuid):
        return bar_storage[uuid]

    def delete(self, uuid):
        del bar_storage[uuid]
```

Key ideas:

- `__resource__` tells the controller which DM model/resource it works with.
- `create/get/filter/delete` are RA methods which are mapped to HTTP via routes.
- `process_filters=True` on the resource enables automatic parsing of query parameters.

---

## 4. Routes

Routes map URLs and HTTP methods to controller methods.

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

    # Nested route for /foo/<uuid>/bars/
    bars = routes.route(BarRoute1, resource_route=True)


class V1Route(routes.Route):
    """Router for /v1/ path."""

    __controller__ = controllers.RoutesListController
    __allow_methods__ = [routes.FILTER]

    # /v1/foos/
    foos = routes.route(FooRoute)
    # /v1/bars/<uuid>
    bars = routes.route(BarRoute2)


class UserApiApp(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


# Route to /v1/ endpoint
setattr(UserApiApp, "v1", routes.route(V1Route))
```

- `FooRoute` handles `/v1/foos/` and `/v1/foos/<uuid>`.
- `BarRoute1` handles `/v1/foos/<uuid>/bars/`.
- `BarRoute2` handles `/v1/bars/<uuid>`.
- `V1Route` and `UserApiApp` group these routes under `/v1/` and root `/`.

---

## 5. WSGI application

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
        [],  # add middleware classes here if needed
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

- `WSGIApp` wraps the root route and builds the `ResourceMap`.
- `middlewares.attach_middlewares` can be used to add logging, error handling, etc.

---

## 6. Trying the API with curl

Assuming the server is running on `http://127.0.0.1:8000`.

### List top-level routes

```bash
curl http://127.0.0.1:8000/
```

### Create a Foo

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/" \
  -H "Content-Type: application/json" \
  -d '{"foo_field1": 10, "foo_field2": "bar"}'
```

### List all Foos

```bash
curl "http://127.0.0.1:8000/v1/foos/"
```

### Get a Foo by UUID

```bash
curl "http://127.0.0.1:8000/v1/foos/<uuid>"
```

### Create a Bar for a specific Foo

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/<uuid>/bars/" \
  -H "Content-Type: application/json" \
  -d '{"bar_field1": "test"}'
```

### Get a Bar by UUID

```bash
curl "http://127.0.0.1:8000/v1/bars/<uuid>"
```

### Delete a Bar by UUID

```bash
curl -X DELETE "http://127.0.0.1:8000/v1/bars/<uuid>"
```

---

## Summary

- DM models define your data.
- Controllers encapsulate business logic for RA methods (FILTER/CREATE/GET/UPDATE/DELETE).
- Routes map HTTP paths/methods to controllers and resources.
- `WSGIApp` ties everything together into a WSGI application.

This pattern scales from simple in-memory examples to production setups with SQL storage and OpenAPI.
