<!--
Copyright 2026 Genesis Corporation

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

# Batch requests（批量请求）

本指南介绍如何使用 `restalchemy.api.batch`，让客户端把多个逻辑操作
（create/get/update/delete，以及 controller actions）合并到一次 HTTP
调用中。

批次中的每个元素都会作为一次独立的请求，原样重放到*未被修改*的
routing/controller/packer 栈中——因此不需要对现有的 `Controller` 或
`Route` 子类做任何改动即可支持批量请求。

---

## 1. 启用该端点

像挂载其他路由一样，把 `batch.BatchRoute` 挂到你的根路由上：

```python
from restalchemy.api import batch
from restalchemy.api import routes


class Root(routes.RootRoute):
    v1 = routes.route(V1Route)
    batch = routes.route(batch.BatchRoute)
```

这会暴露一个单独的 `POST /batch/` 端点，它可以访问从 `Root` 可达的任意
资源——无需为每个资源单独启用。

---

## 2. 请求格式

```json
{
  "requests": [
    {"method": "POST", "path": "/v1/vms/", "body": {"name": "vm-a"}},
    {"method": "GET",  "path": "/v1/vms/<uuid>"},
    {"method": "PUT",  "path": "/v1/vms/<uuid>", "body": {"name": "vm-b"}},
    {"method": "DELETE", "path": "/v1/vms/<uuid>"},
    {"method": "POST", "path": "/v1/vms/<uuid>/actions/poweron/invoke"}
  ]
}
```

`requests` 中每个元素包含：

| 字段      | 是否必填 | 说明                                                        |
|-----------|----------|-------------------------------------------------------------|
| `method`  | 是       | `GET`、`POST`、`PUT` 或 `DELETE`——与真实请求相同。            |
| `path`    | 是       | 你原本会直接调用的路径，如需过滤请包含 query string（`?field=value`）。 |
| `body`    | 否       | JSON 请求体，格式与真实端点所要求的一致。                     |
| `headers` | 否       | 仅作用于该元素的额外请求头。                                  |

---

## 3. 每个元素独立执行，并经过完整的中间件栈

每个元素都以 best-effort 方式独立执行：某一个元素失败不会中断或回滚其他
元素。响应始终是 `200 OK`，每个元素都带有自己的 `status`/`body`，即使部
分元素失败——请单独检查每个元素的 `status`，不要仅凭外层 HTTP 状态码判断
是否成功。

每个元素都会经过包裹在 `/batch` 端点外面的*完整* WSGI 中间件链（鉴权、
按路由的授权/策略、限流、死锁重试等），而不仅仅是内部的
routing/controller 层。因此，批次中的一个元素所受到的规则，与直接调用
同一路径完全一致：如果某个中间件会拒绝或限流一个直接的
`POST /v1/vms/`，那么当同样的请求以批次元素的形式到达时，也会被同样
拒绝。

每个元素都经过完整中间件栈这一点也带来一个后果：如果应用的
`ContextMiddleware` 会为每个请求开启一个数据库事务，那么每个元素都会得
到*属于自己*的事务——不存在跨元素的原子性。一个包含五个写操作的批次，
相当于五个独立的事务，就如同你分别发起了五次独立的直接调用一样；第 3
个元素失败，不会影响第 1、2、4、5 个元素。如果你需要让多个写操作要么
一起成功、要么一起失败，那应该把它实现为针对目标资源本身的一个操作
（即在同一个事务内完成所有更改的单一端点），而不是把多个独立调用打包
成一个批次。

---

## 4. 响应格式

```json
[
  {"status": 201, "body": {"uuid": "...", "name": "vm-a", "...": "..."}},
  {"status": 200, "body": {"uuid": "...", "name": "vm-a", "...": "..."}},
  {"status": 200, "body": {"uuid": "...", "name": "vm-b", "...": "..."}},
  {"status": 204, "body": null},
  {"status": 200, "body": {"uuid": "...", "state": "on", "...": "..."}}
]
```

响应是一个 JSON 数组，每个请求对应一个元素，**顺序与提交时相同**。每个
元素都对应直接调用该端点时会返回的内容：真实的 HTTP 状态码与解析后的
响应体（空响应体则为 `null`）。失败的元素与 RestAlchemy 普通错误体的
格式相同：

```json
{"status": 404, "body": {"type": "RecordNotFound", "code": 404, "message": "..."}}
```

---

## 5. 限制与校验错误

- `requests` 必须是一个 JSON 数组；否则整个调用会抛出 `ParseError`
  （HTTP 400）。
- `BatchController.__max_batch_size__`（默认 `100`）限制单次调用允许包含
  的元素数量；超过该限制会在任何元素执行之前，为整个调用抛出
  `BatchSizeLimitExceeded`（HTTP 400）。如需不同的限制，可在子类中覆盖
  该属性。
- 批次中的元素不能指向 batch 端点本身
  （`NestedBatchNotAllowed`，HTTP 400）——这种调用会被直接拒绝，而不是
  递归执行。

---

## 小结

- `batch.BatchRoute`/`batch.BatchController` 直接复用现有的路由树、
  controller 与 packer，不做任何改动——批量请求功能是纯附加的。
- 每个元素都是 best-effort、相互独立的：请检查每个元素自身的 `status`。
- 元素会经过完整的中间件栈，因此鉴权/策略/限流/重试的行为与直接调用
  完全一致——代价是没有跨元素事务：每个元素都拥有自己的事务。
- Actions（`.../actions/<name>/invoke`）在批次内的行为与直接调用完全
  一致，因为批次中的一个元素本质上就是对 path/method/body 的重放。
