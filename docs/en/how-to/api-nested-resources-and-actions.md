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

# Nested resources and actions

This guide explains how to:

- Implement nested resources (e.g. `/foos/<uuid>/bars/`).
- Implement actions on resources (e.g. `/v1/files/<id>/actions/download`).

It builds on the basic CRUD example and uses ideas from `examples/restapi_foo_bar_service.py` and `examples/openapi_app.py`.

---

## 1. Nested resources

Nested resources represent hierarchical relationships, such as:

- A parent resource: `FooModel` at `/v1/foos/<uuid>`.
- A nested collection: `BarModel` at `/v1/foos/<uuid>/bars/`.

### 1.1. DM models

Same as in the basic CRUD example:

```python
class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

### 1.2. Nested controller

You can use `BaseNestedResourceController` to work with nested resources, or implement a simple controller manually.

Example with explicit parent handling (simplified):

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

Alternatively, `BaseNestedResourceController` provides built-in patterns for parent_resource handling.

### 1.3. Nested route

```python
class BarRoute1(routes.Route):
    __controller__ = BarController1
    __allow_methods__ = [routes.CREATE, routes.FILTER]


class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.FILTER, routes.CREATE, routes.GET]

    bars = routes.route(BarRoute1, resource_route=True)
```

- `resource_route=True` tells RA that `BarRoute1` works with nested resources under a specific parent instance.
- For `/v1/foos/<foo_uuid>/bars/`, RA resolves the parent `FooModel` and passes it as `parent_resource`.

---

## 2. Actions on resources

Actions represent operations that are not pure CRUD on the primary resource. Typical examples:

- `/v1/files/<id>/actions/download` — download a file.
- `/v1/objects/<id>/actions/some_business_operation`.

### 2.1. Defining an action using ActionHandler

Module: `restalchemy.api.actions`

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

- `@actions.get` wraps `download` into an `ActionHandler`.
- The controller method receives `self` as `controller` and `resource` as the current DM instance.
- Use `controller.process_result()` (via `ActionHandler.do_*`) to build a response.

### 2.2. Defining an Action route

```python
from restalchemy.api import routes


class FileDownloadAction(routes.Action):
    """Handler for /v1/files/<id>/actions/download endpoint."""

    __controller__ = FilesController
```

You then attach this action to the resource route:

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

- `routes.action(FileDownloadAction, invoke=True)` declares that:
  - The action is reachable via `/v1/files/<id>/actions/download/invoke`.
  - HTTP methods `GET/POST/PUT` map to `do_get/do_post/do_put` in `ActionHandler`.

### 2.3. Request/response flow for actions

For a URL like `/v1/files/<id>/actions/download/invoke`:

1. `Route.do()` recognizes an `actions` path segment.
2. It fetches the resource by `<id>` using the controller.
3. It resolves the action (`download`).
4. It instantiates `FileDownloadAction` with the request.
5. It calls `Action.do(resource=resource, **kwargs)`.
6. `Action` uses `ActionHandler` to call the right `do_*` method on the wrapped function.

---

## 3. Combining nested resources and actions

Actions can be used on nested resources as well:

- For example, `/v1/foos/<foo_id>/bars/<bar_id>/actions/archive`.

In that case:

- The route tree describes nested routes down to `BarRoute`.
- An `Action` under `BarRoute` can operate on the nested `BarModel` instance.

The pattern is the same as for top-level resources; only the routing path changes.

---

## Summary

- Nested resources are expressed via nested `Route` classes and `resource_route=True`.
- Controllers can use `parent_resource` (or `BaseNestedResourceController`) to implement logic tied to a parent DM instance.
- Actions are implemented via `ActionHandler` decorators and `routes.Action`/`routes.action`, providing a clean way to express non-CRUD operations on resources.
