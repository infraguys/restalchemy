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

本指南展示如何使用 RESTAlchemy 的 API 层构建一个简单的 REST API。

我们将：

- 定义 DM 模型；
- 定义控制器；
- 定义路由；
- 构建 WSGI 应用；
- 使用 `curl` 访问 API。

示例基于 `examples/restapi_foo_bar_service.py`。

---

## 1. DM 模型

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

- `FooModel` 与 `BarModel` 是纯 DM 模型（此处未接存储层，仅在内存中）。
- `BarModel.foo` 表达对 `FooModel` 的关系。

---

## 2. 内存存储（In-memory storage）

为了简化示例，先用 Python 字典存储数据：

```python
foo_storage = {}
bar_storage = {}
```

在真实项目中，你可以将 DM 模型与 SQL 存储（`SQLStorableMixin`）结合使用，API 层用法保持不变。

---

## 3. 控制器（Controllers）

控制器负责将 HTTP 方法映射到 Python 代码。

```python
from restalchemy.api import controllers, resources


class FooController(controllers.Controller):
    """处理 /foos/ 端点。"""

    __resource__ = resources.ResourceByRAModel(FooModel, process_filters=True)

    def create(self, foo_field1, foo_field2):
        foo = self.model(foo_field1=foo_field1, foo_field2=foo_field2)
        foo_storage[str(foo.get_id())] = foo
        return foo

    def get(self, uuid):
        return foo_storage[uuid]

    def filter(self, filters, order_by=None):
        # 简单实现：忽略过滤与排序
        return foo_storage.values()


bar_resource = resources.ResourceByRAModel(BarModel, process_filters=True)


class BarController1(controllers.Controller):
    """处理 /foo/<uuid>/bars/ 端点。"""

    __resource__ = bar_resource

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.get_id())] = bar
        return bar


class BarController2(controllers.Controller):
    """处理 /bars/<uuid> 端点。"""

    __resource__ = bar_resource

    def get(self, uuid):
        return bar_storage[uuid]

    def delete(self, uuid):
        del bar_storage[uuid]
```

要点：

- `__resource__` 指定控制器对应的 DM 模型/资源。
- `create/get/filter/delete` 是 RA 方法，通过路由映射为 HTTP 操作。
- `process_filters=True` 使资源自动解析查询参数为 DM 过滤条件。

---

## 4. 路由（Routes）

路由负责将 URL + HTTP 方法指向控制器方法。

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

    # /foo/<uuid>/bars/ 的嵌套路由
    bars = routes.route(BarRoute1, resource_route=True)


class V1Route(routes.Route):
    """处理 /v1/ 路径。"""

    __controller__ = controllers.RoutesListController
    __allow_methods__ = [routes.FILTER]

    # /v1/foos/
    foos = routes.route(FooRoute)
    # /v1/bars/<uuid>
    bars = routes.route(BarRoute2)


class UserApiApp(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


# 将 V1Route 挂载到 /v1/
setattr(UserApiApp, "v1", routes.route(V1Route))
```

- `FooRoute` 处理 `/v1/foos/` 与 `/v1/foos/<uuid>`。
- `BarRoute1` 处理 `/v1/foos/<uuid>/bars/`。
- `BarRoute2` 处理 `/v1/bars/<uuid>`。
- `V1Route` 与 `UserApiApp` 将各路由归档到 `/v1/` 与根路径 `/`。

---

## 5. WSGI 应用（WSGI application）

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
        [],  # 此处可以挂载中间件
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

---

## 6. 使用 curl 测试 API

假设服务运行在 `http://127.0.0.1:8000`：

查看顶层路由：

```bash
curl http://127.0.0.1:8000/
```

创建 Foo：

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/" \
  -H "Content-Type: application/json" \
  -d '{"foo_field1": 10, "foo_field2": "bar"}'
```

列出所有 Foo：

```bash
curl "http://127.0.0.1:8000/v1/foos/"
```

按 UUID 获取 Foo：

```bash
curl "http://127.0.0.1:8000/v1/foos/<uuid>"
```

为某个 Foo 创建 Bar：

```bash
curl -X POST "http://127.0.0.1:8000/v1/foos/<uuid>/bars/" \
  -H "Content-Type: application/json" \
  -d '{"bar_field1": "test"}'
```

按 UUID 获取 Bar：

```bash
curl "http://127.0.0.1:8000/v1/bars/<uuid>"
```

按 UUID 删除 Bar：

```bash
curl -X DELETE "http://127.0.0.1:8000/v1/bars/<uuid>"
```

---

## 小结

- DM 模型定义数据结构；
- 控制器封装 RA 方法（FILTER/CREATE/GET/UPDATE/DELETE）的业务逻辑；
- 路由将 HTTP 路径/方法映射到控制器与资源；
- `WSGIApp` 将上述组件组合为一个 WSGI 应用。

这一模式可以从简单的内存示例扩展到使用 SQL 存储与 OpenAPI 的生产环境。
