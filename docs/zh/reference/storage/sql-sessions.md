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

# SQL 会话与事务（SQL sessions and transactions）

模块：`restalchemy.storage.sql.sessions`

定义了 PostgreSQL/MySQL 会话、查询缓存以及事务管理辅助工具。

---

## SessionQueryCache

- 基于语句 + 参数生成哈希。
- 在同一会话中缓存 `get_all()` 与 `query()` 结果。

---

## PgSQLSession 与 MySQLSession

- 封装数据库连接与游标。
- 提供 `execute()`、`execute_many()`、`commit()`、`rollback()`、`close()`。
- 支持批量操作 `batch_insert(models)`、`batch_delete(models)`。

---

## session_manager

- `engine.session_manager()` 作为推荐用法：
  - 若未提供会话：内部创建、提交/回滚、关闭会话。
  - 若已提供会话：仅负责透传。

示例：

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    foo = FooModel(foo_field1=42)
    foo.save(session=session)
```

---

## SessionThreadStorage

- 线程本地的会话存储。
- 提供 `store_session()`、`get_session()`、`remove_session()` 等方法。
- 方便在同一线程中复用会话，并与外部事务管理集成。
