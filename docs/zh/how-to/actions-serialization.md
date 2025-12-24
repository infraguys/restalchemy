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

# Action 返回结果序列化的注意事项

本文档说明 RESTAlchemy 的一个重要细节：**在处理 `actions` 时，如何选择序列化器（packer）以及 resource 字段集合**，以及为什么在资源 `A` 的控制器上声明/绑定的 action，默认会 *按资源 `A`* 来序列化——即使它实际返回的是模型 `B`。

同时给出一个不修改库代码的实用规避方案，并附上 functional tests 中可工作的示例链接。

---

## TL;DR

- Action 总是在其声明/绑定的 **controller 上下文中** 执行。
- **packer 与序列化 schema 来自该 controller 的 `__resource__`。**
- 如果 action 返回了不同类型的模型，packer 会尝试读取“错误的字段”，并以 `AttributeError` 失败。
- 不修改 RESTAlchemy 的实用方案：**将该 action 绑定到一个专用 controller**，并让该 controller 的 `__resource__` 与返回模型类型一致。

---

## 1. 为什么会这样

### 1.1 Action 处理流程（概览）

以如下 URL 为例：

- `/v1/vms/<uuid>/actions/ip_addresses`

简化后的流程是：

1. Router 解析路由树（例如 `v1 → vms → actions/ip_addresses`）。
2. 通过 `<uuid>` 加载 VM（这是 action 的 **输入**）。
3. 解析 action 类（`routes.Action`），选择其 `__controller__`。
4. 调用 controller 中使用 `@actions.get` / `@actions.post` 装饰的方法。
5. 将结果传入 `controller.process_result()`。
6. `process_result()` 通过 `controller.get_packer()` 构造 HTTP response。
7. packer 使用 **`controller.__resource__` 中定义的字段集合** 来序列化。

### 1.2 关键点

packer 不会在运行时根据返回值“推断模型类型”（OpenAPI 标注也不会用于运行时 packing）。它会把响应 **当作 controller 绑定的 resource 类型** 来序列化。

如果 controller 声明：

- `__resource__ = ResourceByRAModel(models.VM)`

那么 packer 就会认为对象包含 VM 字段（例如 `state`、`name` 等）。

---

## 2. 问题表现

### 2.1 常见错误

如果 VM controller 的 action 返回 `IpAddress`，packer（按 VM 序列化）会尝试访问 `IpAddress.state`：

- `AttributeError: IpAddress object has no attribute state`

这看起来像 “actions 里序列化坏了”，但本质是 **controller 的 `__resource__` 类型与 action 的实际返回类型不一致**。

---

## 3. Functional tests 中的实践示例（VM → IpAddress）

### 3.1 目标

实现 action endpoint：

- `GET /v1/vms/<uuid>/actions/ip_addresses`

返回该 VM 的 **`IpAddress` 列表**。

### 3.2 为什么不能直接在 `VMController` 里返回 `IpAddress`

如果直接在 `VMController` 中实现 `ip_addresses()` 并返回 `IpAddress`，仍然会按 VM 序列化并失败（见第 2 节）。

### 3.3 不修改库代码的修复方案（方案 1）

该方案包含两部分：

- **(A) 为 action 返回值建立专用 controller**，并设置正确的 `__resource__`。
- **(B) 将 `routes.Action` 绑定到该 controller**。

#### A) 返回值 controller

文件：

- `restalchemy/tests/functional/restapi/ra_based/microservice/controllers.py`

类：

- `VMIpAddressesController`

思路：输入参数 `resource` 仍然是 VM（父资源），但 **`__resource__` 设置为 IpAddress**，因此 packer 能正确序列化返回列表。

额外注意：RESTAlchemy 维护全局的 `model → resource` 映射。

- 如果再创建一个新的 `ResourceByRAModel(models.IpAddress)`，会触发 duplicate mapping 错误。
- 因此这里 **复用** 已存在的 resource：`IpAddressController.__resource__`。

#### B) Action route

文件：

- `restalchemy/tests/functional/restapi/ra_based/microservice/routes.py`

类：

- `VMIPAddressesAction`

该类应指向 `VMIpAddressesController`；在 `VMRoute` 中声明：

- `ip_addresses = routes.action(VMIPAddressesAction, invoke=False)`

### 3.4 验证行为的测试

文件：

- `restalchemy/tests/functional/restapi/ra_based/test_resources.py`

测试：

- `TestRetryOnErrorMiddlewareBaseResourceTestCase.test_vm_get_ip_addresses_action_returns_success`

断言：

- HTTP 200
- JSON 响应是 IpAddress 对象列表，包含：
  - `uuid`
  - `ip`
  - `port`（port 的 URI）

---

## 4. 建议

### 4.1 什么时候使用专用 controller（推荐）

当满足以下条件时，建议使用专用 controller：

- action 返回 **不同的模型类型**（或该类型列表）；
- 希望保留 action endpoint（而不是额外定义一个 nested route）；
- 不希望修改 RESTAlchemy。

它能提供：

- 正确的 packer；
- 正确的字段集合；
- 可预测的行为。

### 4.2 什么时候返回 `dict` / 基础类型

如果返回值不是 resource/model（例如 `{"state": "on"}`），直接返回 `dict`、`list[dict]`、字符串等更合适，因为它们不会依赖 `__resource__` 字段。

### 4.3 一个 action 返回多种类型

如果一个 action 可能返回不同类型（有时 VM，有时 IpAddress），这是不好的接口契约：

- 单一 `__resource__` 无法同时正确序列化两种类型。

建议：

- 拆分成多个 endpoint/controller；
- 或扩展库能力（例如 “action-specific resource type”）。

---

## 5. 另请参阅

- Nested resources 与 actions 的 How-to：
  - `docs/zh/how-to/api-nested-resources-and-actions.md`
