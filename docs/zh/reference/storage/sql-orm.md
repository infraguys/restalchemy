# SQL ORM Mixin 与集合

模块：`restalchemy.storage.sql.orm`

为 DM 模型提供 ORM 风格的功能：

- `ObjectCollection`：集合 API（`Model.objects`）。
- `SQLStorableMixin`：为模型添加 SQL 持久化能力。
- `SQLStorableWithJSONFieldsMixin`：用于 JSON 字段的扩展。

---

## ObjectCollection

常用方法：

- `get_all(...)`：返回模型列表。
- `get_one(...)`：返回一个模型或抛出异常。
- `get_one_or_none(...)`：返回一个模型或 `None`。
- `query(...)`：自定义 WHERE 条件查询。
- `count(...)`：返回行数。

---

## SQLStorableMixin

- 要求定义 `__tablename__` 与 ID 属性。
- `get_table()`：返回模型对应的 `SQLTable`。
- `insert()`、`save()`、`update()`、`delete()`：对表执行 CRUD。
- `restore_from_storage()`：从数据库记录还原为 DM 模型。

`Model.objects` 基于 `ObjectCollection` 实现。

---

## SQLStorableWithJSONFieldsMixin

- 定义 `__jsonfields__` 列表，指定哪些字段存放 JSON 数据。
- 重写 `restore_from_storage()` 与 `_get_prepared_data()`，负责 JSON 的序列化/反序列化。
