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

# 快速上手

本指南将带你构建一个很小的 REST 服务，它：

- 使用内存存储（不需要数据库）。
- 使用一个简单的 DM 模型。
- 使用最小化的 API 层（控制器 + 路由）。
- 作为 WSGI 应用运行。

完成后，你将获得一个运行在 `http://127.0.0.1:8000/` 的 HTTP API。

---

## 1. 项目结构

创建目录和文件：

```text
myservice/
  app.py
```

下面所有代码都写在 `app.py` 中。

---

## 2. 简单 DM 模型

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

`FooModel` 是一个 DM 模型：

- 继承自 `ModelWithUUID`，自动生成 UUID 主键。
- 拥有一个整数字段 `value`。

---

## 3. 内存存储

先用一个字典作为简单存储：

```python
FOO_STORAGE = {}
```

---

## 4. 控制器

控制器实现 `CREATE`、`GET` 和 `FILTER` 三种操作：

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

## 5. 路由

路由负责将 URL 和方法映射到控制器：

```python
class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.CREATE, routes.GET, routes.FILTER]


class ApiRoot(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]

    foos = routes.route(FooRoute)
```

这样：

- `GET /` —— 根路由。
- `POST /foos/` —— 创建新的 `FooModel`。
- `GET /foos/<uuid>` —— 获取单个对象。
- `GET /foos/` —— 获取所有对象列表。

---

## 6. 构建 WSGI 应用

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

## 7. 启动服务

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

运行：

```bash
python app.py
```

---

## 8. 测试 API

创建一个 `Foo`：

```bash
curl -X POST "http://127.0.0.1:8000/foos/" \
  -H "Content-Type: application/json" \
  -d '{"value": 42}'
```

列出所有对象：

```bash
curl "http://127.0.0.1:8000/foos/"
```

获取单个对象（替换 `<uuid>`）：

```bash
curl "http://127.0.0.1:8000/foos/<uuid>"
```

---

## 9. 后续步骤

完成这个最小 in-memory 服务之后，你可以：

- 迁移到 SQL 存储（参见 `concepts/data-model.md`、`concepts/storage-layer.md` 以及 DM+SQL 指南）。
- 查看完整示例 `examples/restapi_foo_bar_service.py`。
- 在 How-to 文档中学习过滤、关系等更高级的用法。
