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

# RESTAlchemy

RESTAlchemy 是一个用于构建 HTTP REST API 的 Python 工具集，它基于灵活的数据模型和存储抽象。

它包含：

- **Data Model (DM)** 层：定义领域模型并进行校验。
- **Storage** 层：对接持久化存储（例如 SQL 数据库）。
- **API** 层：将模型暴露为 REST 风格的 HTTP 资源。
- 可选的 **OpenAPI** 支持：生成和提供接口文档。

文档提供四种语言版本：

- 英文 (`docs/en`)
- 俄文 (`docs/ru`)
- 德文 (`docs/de`)
- 中文 (`docs/zh`)

各语言的文件结构和章节完全一致。

---

## 核心概念

### Data Model (DM)

DM 负责：

- 声明模型和字段。
- 校验值和类型。
- 描述模型之间的关系。

通常通过继承 DM 基类（例如 `ModelWithUUID`），并使用 `properties` 和 `types` 来定义字段。

### Storage

Storage 层提供：

- 对 SQL 引擎（MySQL、PostgreSQL 等）的抽象。
- 会话和事务。
- 查询和过滤的辅助工具。

你可以先只使用内存存储（in-memory），之后再接入 SQL 存储。

### API

API 层包括：

- 实现业务逻辑的控制器。
- 描述如何通过 HTTP 暴露 DM 模型的资源。
- 将 URL 和 HTTP 方法映射到控制器的路由。
- 中间件和 WSGI 应用。

你可以先从一个非常小的内存服务开始，然后逐步引入 DM 和 Storage 以满足生产需求。

### OpenAPI（可选）

OpenAPI 集成可以：

- 从控制器和路由自动生成 OpenAPI 规范。
- 通过接口提供 OpenAPI 文档。
- 配合 Swagger UI 或客户端代码生成器一起使用。

---

## 适用场景

在以下情况下 RESTAlchemy 非常有用：

- **你希望** 清晰地分离：
  - 领域数据模型（DM），
  - 存储实现细节，
  - HTTP API，  
  又不想使用过于庞大的框架。
- **你需要** 强类型、可校验的数据模型。
- **你想要** 以最少样板代码快速暴露 REST 资源。
- **你关心** 数据库迁移和模式演进。

---

## 快速导航

新用户建议阅读顺序：

1. [Installation](installation.md)
2. [Getting started](getting-started.md) —— 构建一个内存中的小型 REST 服务。
3. 概念：
   - [Data model](concepts/data-model.md)
   - [API layer](concepts/api-layer.md)
   - [Storage layer](concepts/storage-layer.md)
4. 实战指南（How-to）：
   - 基本 CRUD
   - 过滤、排序与分页
   - 模型关系
5. 参考文档：
   - `restalchemy.api.*`
   - `restalchemy.dm.*`
   - `restalchemy.storage.*`

只阅读：

- `installation.md`
- `getting-started.md`

就应该能搭建出一个可运行的服务。

---

## 示例

实际代码示例位于仓库的 `examples/` 目录，特别是：

- `examples/restapi_foo_bar_service.py`  
  使用内存存储的简单 REST 服务。
- `examples/dm_mysql_storage.py`  
  使用 MySQL 存储的数据模型示例。
- `examples/openapi_app.py`  
  带有 OpenAPI 规范的 API 示例。
