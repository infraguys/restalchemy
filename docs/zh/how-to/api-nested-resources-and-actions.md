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

# 嵌套资源与 Actions

本指南说明如何：

- 实现嵌套资源（例如 `/foos/<uuid>/bars/`）；
- 在资源上实现 Actions（例如 `/v1/files/<id>/actions/download`）。

它基于 basic CRUD 示例，并参考 `examples/restapi_foo_bar_service.py` 与 `examples/openapi_app.py` 中的模式。

---

## 1. 嵌套资源（Nested resources）

嵌套资源用于表达层级关系，例如：

- 父资源：`FooModel`，URL 为 `/v1/foos/<uuid>`；
- 嵌套集合：`BarModel`，URL 为 `/v1/foos/<uuid>/bars/`。

### 1.1 DM 模型

与 basic CRUD 示例相同：

```python
class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

### 1.2 嵌套控制器

你可以使用 `BaseNestedResourceController`，也可以在自定义控制器中显式处理 `parent_resource`。

```python
class BarController1(controllers.Controller):
    """处理 /v1/foos/<uuid>/bars/。"""

    __resource__ = resources.ResourceByRAModel(BarModel, process_filters=True)

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.get_id())] = bar
        return bar

    def filter(self, filters, parent_resource, order_by=None):
        # 简单示例：只返回指定 Foo 下的 Bar
        return [
            bar for bar in bar_storage.values() if bar.foo == parent_resource
        ]
```

如果使用 `BaseNestedResourceController`，它会对 `parent_resource` 的处理进行一定封装。

### 1.3 嵌套路由

```python
class BarRoute1(routes.Route):
    __controller__ = BarController1
    __allow_methods__ = [routes.CREATE, routes.FILTER]


class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.FILTER, routes.CREATE, routes.GET]

    bars = routes.route(BarRoute1, resource_route=True)
```

- `resource_route=True` 表示 `BarRoute1` 是在某个父资源实例（`FooModel`）之下的“资源路由”；
- 对于 `/v1/foos/<foo_uuid>/bars/`，RA 会解析 `<foo_uuid>` 对应的父资源，并以 `parent_resource` 传入控制器。

---

## 2. 资源 Actions

Actions 表示不直接等同于 CRUD 的操作，例如：

- `/v1/files/<id>/actions/download` —— 下载文件；
- `/v1/objects/<id>/actions/some_business_operation` —— 自定义业务操作。

### 2.1 使用 ActionHandler 定义 Action

模块：`restalchemy.api.actions`

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
        # resource 表示文件描述，可通过其方法取回二进制内容
        data = resource.download_file()
        headers = {
            "Content-Type": constants.CONTENT_TYPE_OCTET_STREAM,
            "Content-Disposition": f'attachment; filename="{resource.name}"',
        }
        return data, 200, headers
```

- `@actions.get` 将 `download` 封装为 `ActionHandler`；
- 控制器方法接收 `self` 作为 `controller`，`resource` 为当前 DM 实例；
- 实际返回值通过 `controller.process_result()`（在 `ActionHandler.do_*` 内部调用）封装为 HTTP 响应。

### 2.2 定义 Action 路由

```python
from restalchemy.api import routes


class FileDownloadAction(routes.Action):
    """处理 /v1/files/<id>/actions/download 端点。"""

    __controller__ = FilesController
```

在资源路由中挂载该 Action：

```python
class FilesRoute(routes.Route):
    """处理 /v1/files/<id> 端点。"""

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

- `routes.action(FileDownloadAction, invoke=True)` 表示：
  - Action 可以通过 `/v1/files/<id>/actions/download/invoke` 访问；
  - HTTP `GET/POST/PUT` 会映射到 `ActionHandler` 的 `do_get/do_post/do_put`。

### 2.3 Actions 的请求/响应流程

以 `/v1/files/<id>/actions/download/invoke` 为例：

1. `Route.do()` 识别路径中的 `actions` 段；
2. 控制器根据 `<id>` 加载对应资源；
3. 查找到名为 `download` 的 Action；
4. 用当前请求实例化 `FileDownloadAction`；
5. 调用 `Action.do(resource=resource, **kwargs)`；
6. `Action` 内部通过 `ActionHandler` 调用对应的 `do_*` 方法，并返回结果。

---

## 3. 组合嵌套资源与 Actions

Actions 同样可以用于嵌套资源，例如：

- `/v1/foos/<foo_id>/bars/<bar_id>/actions/archive`。

在这种情况下：

- 路由树向下延伸到 `BarRoute`；
- `BarRoute` 下的某个 `Action` 将在对应的 `BarModel` 实例上运行。

模式与顶层资源基本相同，只是路径更长、结构更复杂。

---

## 小结

- 使用嵌套 `Route` 类与 `resource_route=True` 可以表达嵌套资源结构；
- 控制器可通过 `parent_resource` 或 `BaseNestedResourceController` 处理父子关系；
- 结合 `ActionHandler` 装饰器与 `routes.Action`/`routes.action`，可以优雅地为资源定义非 CRUD 型操作端点。
