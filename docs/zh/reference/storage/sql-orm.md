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

# SQL ORM Mixin 与集合

模块：`restalchemy.storage.sql.orm`

为 DM 模型提供 ORM 风格的功能：

- `ObjectCollection`：集合 API，以 `Model.objects` 暴露。
- `SQLStorableMixin`：为模型添加 `save()`、`update()`、`delete()` 以及与 SQL 表的集成。
- `SQLStorableWithJSONFieldsMixin`：面向含 JSON 字段模型的特化。

---

## ObjectCollection

`ObjectCollection` 为使用 SQL 存储的模型实现集合接口。

常用方法：

- `get_all(filters=None, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - 返回模型实例列表。
  - 使用 `filters`（DM 过滤结构）构建 WHERE 条件。
  - `cache=True` 时可使用会话级查询缓存。
- `get_one(filters=None, session=None, cache=False, locked=False)`
  - 返回且仅返回一个模型实例。
  - 无结果时抛出 `RecordNotFound`，多于一条时抛出 `HasManyRecords`。
- `get_one_or_none(filters=None, session=None, cache=False, locked=False)`
  - 返回单个实例；若未找到则返回 `None`。
- `query(where_conditions, where_values, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - 执行自定义的 WHERE 条件。
- `count(session=None, filters=None)`
  - 返回符合过滤条件的行数。

`ObjectCollection` 依赖：

- 通过 `engine.dialect` 获得的 SQL 方言。
- 模型的 `restore_from_storage()` 方法，把数据库记录转换为 DM 模型。

### 关联对象的加载

查询未预取（`prefetch`）的关联以标识符的形式返回，它所指向的模型需要单独读取。
`get_all()` 与 `query()` 会收集整页的标识符，按关联发出一次查询，而不是按行发出
一次查询；对这些对象自身所指向的关联也同样处理。

- 页内指向同一对象的记录，拿到的是同一个实例。
- 页内没有找到的标识符会原样保留，因此指向缺失记录的行仍会像以前那样失败。
- 以 `prefetch=True` 声明的关联由读取该页的同一条查询（`LEFT JOIN`）读取，不参与
  此过程。
- `SQLStorableMixin.RELATIONSHIP_BATCH_SIZE`（默认 1000）限制单条查询请求的标识符
  数量。

---

## SQLStorableMixin

`SQLStorableMixin` 用于与 DM 模型组合，使其可以持久化到 SQL。

### 前置要求

- DM 模型必须定义合法的 `__tablename__` 字符串。
- 至少要有一个 ID 属性（`id_property=True`）。

### 核心职责

- `get_table()`
  - 返回模型对应的 `SQLTable` 实例，并缓存在 `__operational_storage__` 中。
- `insert(session=None)`
  - 使用当前属性值把模型插入表中。
  - 将方言相关的异常包装为存储层异常（例如冲突）。
- `save(session=None)`
  - 如果实例尚未保存，则调用 `insert()`。
  - 否则调用 `update()`。
- `update(session=None, force=False)`
  - 当模型被修改或 `force=True` 时更新该行。
  - 更新前会校验模型。
  - 确保恰好更新一行（否则抛出异常）。
- `delete(session=None)`
  - 删除与模型 ID 属性对应的行。
- `restore_from_storage(**kwargs)`（类方法）
  - 把数据库记录中的值（简单类型）转换为 DM 属性值。
  - 构造一个被标记为已保存的模型实例。

### 集合绑定

`SQLStorableMixin` 定义了 `_ObjectCollection = ObjectCollection`。与基础存储类配合后即可得到：

- `Model.objects`：通过 `ObjectCollection` 执行查询的集合对象。

### 类型转换辅助方法

- `to_simple_type(value)`（类方法）
  - 把模型实例或原始 ID 值转换为适合用于过滤条件的形式。
- `from_simple_type(value)`（类方法）
  - 把原始 ID 值或 prefetch 结果转换为模型实例。

借助这些方法，存储层与 API 层可以透明地处理 ID 与 prefetch 结构。

---

## SQLStorableWithJSONFieldsMixin

`SQLStorableWithJSONFieldsMixin` 扩展自 `SQLStorableMixin`，面向不原生支持 JSON 字段的数据库。

使用方式：

- 继承 `SQLStorableWithJSONFieldsMixin` 而不是 `SQLStorableMixin`。
- 把存放 JSON 数据的字段名定义为可迭代对象 `__jsonfields__`。

行为：

- `restore_from_storage()`
  - 对 `__jsonfields__` 中列出的字段：
    - 如果存储的值是字符串，则按 JSON 解析。
- `_get_prepared_data(properties=None)`
  - 对 `__jsonfields__` 中的字段，把 Python 数据结构序列化为紧凑的 JSON 字符串。

这样即可在 DM 模型中保留 JSON 字段，同时在缺少原生 JSON 支持的数据库中以文本形式持久化。
