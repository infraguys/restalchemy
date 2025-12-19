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

# DM + SQL storage how-to

本指南展示如何使用 RESTAlchemy 将 DM 模型持久化到 SQL 数据库。

你将学会：

- 使用 `ModelWithUUID` 与 `SQLStorableMixin` 定义可持久化的 DM 模型。
- 配置 SQL 引擎（MySQL 或 PostgreSQL）。
- 通过 `.save()`、`.delete()` 与 `Model.objects` 执行 CRUD 操作。
- 使用过滤器构造查询条件。

示例基于 `examples/dm_mysql_storage.py` 与 `examples/dm_pg_storage.py`。

---

## 前置条件

- 已安装 RESTAlchemy（见 `installation.md`）。
- 有一套正在运行的数据库：
  - MySQL/MariaDB，或
  - PostgreSQL。
- 安装了对应的 Python 驱动，例如：
  - `mysql-connector-python`（MySQL）。
  - `psycopg[binary]`（PostgreSQL）。
- 数据库中已存在与模型对应的表结构（可通过迁移工具创建）。

---

## 1. 为 SQL 定义 DM 模型

基本模式：

- 继承自 `models.ModelWithUUID`（或其它 `ModelWithID`）。
- 同时继承 `orm.SQLStorableMixin`。
- 设置 `__tablename__`。
- 使用 DM 属性与类型定义字段。

示例（简化自 `dm_mysql_storage.py`）：

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

---

## 2. 配置 SQL 引擎

通过 `restalchemy.storage.sql.engines.engine_factory` 创建引擎实例。

### MySQL 示例

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/test",
)
```

### PostgreSQL 示例

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="postgresql://postgres:password@127.0.0.1:5432/ra_tests",
)
```

通常在应用启动时调用一次 `configure_factory()`。之后所有带有 `SQLStorableMixin` 的模型会通过 `engine_factory.get_engine()` 获得引擎。

可选参数：

- `config`：引擎配置（连接池大小、超时等）。
- `query_cache`：是否启用会话级查询缓存。

---

## 3. 创建表与迁移

RESTAlchemy 不会自动创建数据表，而是依赖显式迁移。

迁移命令在 `README.rst` 中有说明：

- `ra-new-migration`：创建新的迁移文件。
- `ra-apply-migration`：应用迁移。

示例文件中包含注释形式的 SQL DDL（例如 `dm_mysql_storage.py`），可按需调整或通过迁移工具生成类似结构。

---

## 4. 基本 CRUD 操作

在配置好引擎并创建表之后，可以像操作普通 DM 模型一样进行 CRUD：

### 创建与保存

```python
foo1 = FooModel(foo_field1=10)
foo1.save()

bar1 = BarModel(bar_field1="test", foo=foo1)
bar1.save()
```

### 读取数据

```python
# 所有 Bar
all_bars = list(BarModel.objects.get_all())

# 根据主键读取一个 Bar
same_bar = BarModel.objects.get_one(filters={"uuid": bar1.get_id()})

# 获取某个 Foo 下的所有 Bar
bars_for_foo = list(BarModel.objects.get_all(filters={"foo": foo1}))

print(bar1.as_plain_dict())
```

### 更新

```python
foo2 = FooModel(foo_field1=11, foo_field2="some text")
foo2.save()

foo2.foo_field2 = "updated text"
foo2.save()
```

### 删除

```python
for foo in FooModel.objects.get_all():
    foo.delete()
```

---

## 5. 过滤（Filters）

过滤器来自 `restalchemy.dm.filters`，可传递给 `get_all()` 和 `get_one()`：

```python
from restalchemy.dm import filters

one = FooModel.objects.get_one(filters={"foo_field1": filters.EQ(10)})

greater = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.GT(5)})
)

subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.In([5, 6])})
)

not_subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.NotIn([1, 2])})
)
```

更复杂的逻辑可以使用 `AND` / `OR`：

```python
filter_expr = filters.OR(
    filters.AND({
        "foo_field1": filters.EQ(1),
        "foo_field2": filters.EQ("2"),
    }),
    filters.AND({"foo_field2": filters.EQ("3")}),
)

foo = FooModel.objects.get_one(filters=filter_expr)
```

---

## 6. 事务与显式会话

默认情况下，每次操作使用独立的会话与事务。

若需要将多次操作合并到一个事务中，可以使用 `engine.session_manager()`：

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    foo = FooModel(foo_field1=42)
    foo.save(session=session)

    bar = BarModel(bar_field1="x", foo=foo)
    bar.save(session=session)
```

`with` 代码块中的所有操作都在一个事务中执行，如有异常会统一回滚。

---

## 小结

- 通过 `ModelWithUUID` + `SQLStorableMixin` 定义持久化模型，并设置 `__tablename__`。
- 使用 `engine_factory.configure_factory()` 配置 SQL 引擎。
- 使用迁移工具创建/更新数据库表。
- 使用 `.save()`、`.delete()`、`Model.objects.get_all()/get_one()` 实现 CRUD。
- 使用 DM 过滤器表示查询条件。
- 在需要时通过显式会话控制事务边界。
