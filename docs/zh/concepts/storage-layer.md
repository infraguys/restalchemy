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

# 存储层（Storage layer）

RESTAlchemy 中的存储层负责将 DM 模型持久化到数据库，并从中读取。

它作为独立一层位于 Data Model (DM) 与 API 之间。

---

## 模块概览

与 SQL 存储相关的主要模块：

- `restalchemy.storage.base`
  - 可持久化模型与集合的抽象接口。
- `restalchemy.storage.exceptions`
  - 存储层异常。
- `restalchemy.storage.sql.engines`
  - 引擎工厂以及 MySQL/PostgreSQL 的具体实现。
- `restalchemy.storage.sql.sessions`
  - 数据库会话、事务以及每会话查询缓存。
- `restalchemy.storage.sql.orm`
  - ORM 风格的 Mixin 与集合（`SQLStorableMixin`、`ObjectCollection`）。
- `restalchemy.storage.sql.tables`
  - ORM 与方言使用的表抽象。
- `restalchemy.storage.sql.dialect.*`
  - 针对不同数据库的 SQL 方言实现。

一般情况下，你只需要接触：

- DM 模型 + `orm.SQLStorableMixin`；
- `engines.engine_factory.configure_factory()` 进行引擎配置；
- `Model.objects` 以及实例上的 `save()` / `delete()`。

---

## 架构概览

### 1. DM 模型

你定义一个模型，同时继承：

- `models.ModelWithUUID`（或其他 `Model*` 基类），以及
- `orm.SQLStorableMixin`。

示例（基于 `examples/dm_mysql_storage.py`）：

```python
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "bars"
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

### 2. 引擎与会话

`restalchemy.storage.sql.engines` 提供 `engine_factory`，用于管理 SQL 引擎。

配置示例：

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/mydb",
)
```

关键点：

- **Engine** 负责解析 `db_url`、建立连接池并选择合适的方言。
- **Session**（`PgSQLSession` / `MySQLSession`）负责执行 SQL 语句。
- `session_manager(engine, session=None)`（在 `sessions.py` 中）将会话使用包裹为事务边界。

### 3. ORM Mixin 与集合

`restalchemy.storage.sql.orm` 提供：

- `SQLStorableMixin`：为 DM 模型提供 SQL 持久化能力。
- `ObjectCollection`：通过 `Model.objects` 暴露的集合 API。

职责：

- **`SQLStorableMixin`**：
  - 通过 `__tablename__` 与 `get_table()` 将模型绑定到数据库表。
  - 实现 `insert()`、`save()`、`update()`、`delete()`。
  - 在 DM 属性与存储格式之间进行转换。

- **`ObjectCollection`**：
  - 提供 `get_all()`、`get_one()`、`get_one_or_none()`、`query()`、`count()` 等方法。
  - 使用 `restalchemy.dm.filters` 来表达 WHERE 条件。

### 4. 方言与表

`restalchemy.storage.sql.dialect.*` 模块与 `tables.SQLTable`：

- 负责构造 SQL 语句（SELECT/INSERT/UPDATE/DELETE）。
- 绑定参数并执行查询。

通常无需直接使用这些模块，它们由模型与集合在内部驱动。

---

## SQL 支持模型的生命周期

1. **定义模型**
   - 继承自 `ModelWithUUID` 和 `SQLStorableMixin`。
   - 设置 `__tablename__`。
   - 使用 DM 属性与类型定义字段和关系。

2. **配置引擎**
   - 在应用启动时调用一次 `engine_factory.configure_factory(db_url=...)`。

3. **创建表 / 迁移**
   - 使用迁移工具（`ra-new-migration`、`ra-apply-migration`）创建/更新数据库结构。

4. **执行 CRUD 操作**
   - 创建模型实例并调用 `.save()`。
   - 使用 `Model.objects.get_all()` / `.get_one(filters=...)` 读取数据。
   - 调用 `.delete()` 删除记录。

5. **过滤与复杂查询**
   - 使用 `restalchemy.dm.filters` 构造过滤条件并传入 `objects.get_all()` / `get_one()`。

6. **事务与会话（可选）**
   - 当你需要更精细的事务控制时，可以显式使用 `session_manager()` 将多次操作包在同一事务中。

这些步骤会在 DM+SQL 指南以及 `examples/dm_mysql_storage.py`、`examples/dm_pg_storage.py` 中有更完整的示例展示。
