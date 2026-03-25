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

# API 层（API layer）

RESTAlchemy 中的 API 层负责在 HTTP 请求与 DM 模型以及存储层之间建立映射。

它的主要职责：

- 将 HTTP 路径和方法路由到对应的控制器；
- 将控制器映射到基于 DM 模型的资源；
- 处理请求/响应体的序列化与反序列化；
- 应用字段级别的权限与过滤逻辑；
- （可选）提供 OpenAPI 规范。

---

## 核心构件

### 1. Applications

模块：`restalchemy.api.applications`

- `WSGIApp` / `Application`：
  - WSGI 服务器入口；
  - 接收根路由类（`routes.Route` 的子类）；
  - 通过 `routes.Route.build_resource_map()` 与 `resources.ResourceMap.set_resource_map()` 构建 ResourceMap；
  - 每个请求：
    - 创建 `RequestContext`；
    - 调用主路由的 `do()` 方法。

- `OpenApiApplication(WSGIApp)`：
  - 在 `WSGIApp` 基础上增加 `openapi_engine`；
  - 用于对外提供 OpenAPI 端点。

### 2. Routes

模块：`restalchemy.api.routes`

- `BaseRoute`：
  - 通过 `__controller__` 知道哪个控制器负责处理该路由；
  - 通过 `__allow_methods__` 声明允许的 RA 方法；
  - 定义抽象方法 `do()` 处理请求。

- `Route(BaseRoute)`：
  - 表达集合路由与资源路由；
  - 将 HTTP 方法映射为 RA 方法（`FILTER/CREATE/GET/UPDATE/DELETE`）；
  - 将请求委托给控制器的 `do_collection`、`do_resource` 或嵌套路由 / actions；
  - 支持生成 OpenAPI 路径与操作。

- `Action(BaseRoute)`：
  - 处理 `/actions/` 路径下针对资源的操作。

- 辅助函数：
  - `route(route_class, resource_route=False)`：标记嵌套路由是集合路由还是资源路由；
  - `action(action_class, invoke=False)`：定义 Action 是否使用 `/invoke` 语义。

### 3. 控制器（Controllers）

模块：`restalchemy.api.controllers`

- `Controller`：
  - 所有控制器的基类；
  - 通过 `__resource__` 绑定到某个资源；
  - 负责通过 packer 将 Python 对象打包成响应，或从请求体解包；
  - 实现 `process_result()`，将业务层返回值转换为 `webob.Response`。

- `BaseResourceController` 及其变体：
  - 为 DM 模型实现标准 RA 方法：`create`、`get`、`filter`、`update`、`delete`；
  - 支持排序、过滤、分页以及自定义过滤逻辑。

- `RoutesListController`、`RootController`：
  - 用于列出可用路由（`/`、`/v1/`）。

- `OpenApiSpecificationController`：
  - 基于配置的 `openapi_engine` 生成并返回 OpenAPI 规范文档。

### 4. 资源（Resources）

模块：`restalchemy.api.resources`

- `ResourceMap`：
  - 全局保存 DM 模型类型与资源、资源与 URL 之间的映射；
  - 用于构建 `Location` 头以及根据 URI 查找资源。

- `ResourceByRAModel`：
  - 描述一个 DM 模型在 API 中的呈现方式：
    - 哪些字段是公开字段；
    - 如何在模型属性与 API 字段之间进行转换；
  - 被 packer 与 Controller 在处理请求时使用。

### 5. Packer

模块：`restalchemy.api.packers`

- `BaseResourcePacker`：
  - 将资源序列化为简单类型（`dict`、`list`、标量）；
  - 将请求体反序列化为 DM 模型字段值。

- `JSONPacker` 与 `JSONPackerIncludeNullFields`：
  - 在 JSON 与 DM 资源数据之间转换。

- `MultipartPacker`：
  - 处理 `multipart/form-data` 请求（例如文件上传）。

### 6. Context 与字段权限

- `contexts.RequestContext`：
  - 挂载在请求对象上（`req.api_context`）；
  - 记录当前活动的 RA 方法（`FILTER/CREATE/...`）；
  - 提供原始参数和过滤参数的访问接口。

- 模块 `field_permissions`：
  - `UniversalPermissions`、`FieldsPermissions`、`FieldsPermissionsByRole`；
  - 控制字段是否隐藏（`HIDDEN`）、只读（`RO`）或可读写（`RW`），并可以按方法与角色区分。

### 7. Actions

模块：`restalchemy.api.actions`

- `ActionHandler` 与装饰器：
  - `@actions.get`、`@actions.post`、`@actions.put`；
  - 为资源上的操作实现特定 HTTP 方法的行为。

配合 `routes.Action` 与 `routes.action`，可以非常自然地表达诸如 `/v1/files/<id>/actions/download` 这类操作端点。

---

## 请求/响应流程概览

1. **HTTP 请求到达** WSGI 服务器；
2. 调用 `WSGIApp.__call__`：
   - 创建 `RequestContext`，并挂载到 `req.api_context`；
   - 调用根路由 `main_route(req).do()`；
3. **Route**（`Route` 或 `Action`）检查 `req.path_info` 与 `req.method`：
   - 解析嵌套路由与 actions；
   - 确定相应的 RA 方法（FILTER/CREATE/GET/UPDATE/DELETE 或某个 action）；
   - 实例化控制器，并将控制权交给它；
4. **Controller**：
   - 从 `RequestContext` 中解析过滤、排序和分页信息；
   - 与资源与 DM 模型进行交互（并间接调用存储层）；
   - 通过 `process_result()` 与 packer 将 Python 对象转换为 `webob.Response`；
5. **响应** 返回给客户端。

OpenAPI 集成利用同样的 routes/controllers/resources 来构建规范文档，并由 `OpenApiSpecificationController` 通过 `OpenApiApplication` 对外提供。
