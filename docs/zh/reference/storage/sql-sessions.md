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

本模块定义了 PostgreSQL 与 MySQL 的会话类、查询缓存，以及管理会话的辅助工具。

---

## SessionQueryCache

`SessionQueryCache` 是会话级别的查询结果缓存。

- 基于 SQL 语句与绑定参数计算哈希。
- 缓存 `get_all()` 与 `query()` 的结果。
- 在同一会话中再次执行相同查询时复用缓存结果。

当 `cache=True` 时，由 `PgSQLSession` 与 `MySQLSession` 在内部使用。

---

## PgSQLSession

`PgSQLSession` 封装 PostgreSQL 的连接与游标：

- 通过 `engine.get_connection()` 从 `PgSQLEngine` 获取连接。
- 使用行工厂（`pg_rows.dict_row`）以获得类字典的记录。
- 提供 `execute()`、`execute_many()`、`commit()`、`rollback()`、`close()`。
- 提供 `batch_insert(models)` 与 `batch_delete(models)` 辅助方法：
  - 确保所有模型属于同一类型。
  - 通过 `pgsql` 方言类构建批量 SQL 操作。

会话通常由以下方式管理：

- `AbstractEngine` 的 `engine.session_manager()`，或
- 本模块的 `session_manager(engine, session=None)` 上下文管理器。

---

## MySQLSession

`MySQLSession` 与 `PgSQLSession` 类似，但使用：

- 从 `MySQLEngine` 获取的 MySQL 连接。
- 设置了 `dictionary=True` 的 `mysql.connector` 游标。
- `mysql` 方言类（`MySQLInsert`、`MySQLBatchDelete` 等）。

它同样支持：

- `batch_insert(models)` 与 `batch_delete(models)`。
- 把常见的死锁与完整性错误转换为存储层异常。

---

## session_manager

会话管理有两种相关机制：

1. `engines.AbstractEngine.session_manager()`
2. `sessions.session_manager(engine, session=None)`

`engines.AbstractEngine.session_manager()`：

- 最常用的方式。
- 若未提供会话，它会：
  - 通过 `engine.get_session()` 创建新会话。
  - 把会话交给调用方。
  - 成功时提交，出现异常时回滚。
  - 最后关闭会话。
- 若已提供会话，则仅原样透传，不做额外处理。

`sessions.session_manager(engine, session=None)`：

- 行为类似，实现在 sessions 模块中。
- 如果你已经持有引擎实例，可以直接使用它。

示例：

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    # 在同一个事务中执行多个操作
    foo = FooModel(foo_field1=42)
    foo.save(session=session)
```

---

## SessionThreadStorage

`SessionThreadStorage` 是线程本地的会话存储：

- 每个线程保存一个会话。
- 提供以下方法：
  - `get_session()`：返回已保存的会话，若不存在则抛出 `SessionNotFound`。
  - `store_session(session)`：为当前线程保存会话；若已存在则抛出 `SessionConflict`。
  - `remove_session()` / `pop_session()`：清除，或取出并清除已保存的会话。

引擎以 `SessionThreadStorage` 作为会话存储，从而：

- 会话可以创建一次，并被同一线程中的多个操作复用。
- 上层代码可以把 RESTAlchemy 会话集成进已有的事务管理中。
