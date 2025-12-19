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

# 存储层参考（Storage reference）

本节介绍 RESTAlchemy 中的存储层。

大部分与用户相关的接口位于 `restalchemy.storage.sql.*`，并与 DM 模型和 API 一起使用。

---

## 模块

- `restalchemy.storage.base`
  - 可持久化模型与集合的抽象接口。
- `restalchemy.storage.exceptions`
  - 存储层异常。
- `restalchemy.storage.sql.engines`
  - SQL 引擎工厂与 MySQL/PostgreSQL 实现。
- `restalchemy.storage.sql.sessions`
  - 数据库会话、事务辅助与查询缓存。
- `restalchemy.storage.sql.orm`
  - ORM 风格的 Mixin 与 `ObjectCollection`。
- `restalchemy.storage.sql.tables`
  - 表抽象。
- `restalchemy.storage.sql.dialect.*`
  - SQL 方言实现。

---

## 常见使用入口

1. 配置引擎：

   ```python
   from restalchemy.storage.sql import engines

   engines.engine_factory.configure_factory(
       db_url="mysql://user:password@127.0.0.1:3306/test",
   )
   ```

2. 定义继承 `orm.SQLStorableMixin` 且设置了 `__tablename__` 的 DM 模型。

3. 使用：

   - `Model.objects.get_all()` / `Model.objects.get_one()` 读取数据。
   - 实例上的 `.save()`、`.delete()` 执行写操作。

更多细节：

- [SQL 引擎](sql-engines.md)
- [SQL ORM Mixin 与集合](sql-orm.md)
- [SQL 会话与事务](sql-sessions.md)
