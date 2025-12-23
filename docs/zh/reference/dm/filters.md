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

# 过滤器（Filters）

模块：`restalchemy.dm.filters`

过滤器用于表达针对 DM 模型的查询条件，通常由 Storage 与 API 层解析为实际查询（如 SQL WHERE 条件）。

---

## 子句（Clauses）

所有子句类都继承自 `AbstractClause`，保存一个 `value`。

常见子句：

- `EQ(value)`：等于。
- `NE(value)`：不等于。
- `GT(value)`：大于。
- `GE(value)`：大于等于。
- `LT(value)`：小于。
- `LE(value)`：小于等于。
- `Is(value)`：`IS` 比较（如 `IS NULL`）。
- `IsNot(value)`：`IS NOT`。
- `In(value)`：在集合中。
- `NotIn(value)`：不在集合中。
- `Like(value)`：模糊匹配。
- `NotLike(value)`：模糊匹配取反。

---

## 表达式（Expressions）

表达式用于组合多个子句：

- `ClauseList`：子句列表。
- `AND(*clauses)`：逻辑与。
- `OR(*clauses)`：逻辑或。

这些表达式并不会在 Python 中直接求值，而是由后端（Storage）进行解释并转换为相应查询语句。

---

## 与 DM + SQL Storage 联合使用

简化自 `examples/dm_mysql_storage.py`：

```python
from restalchemy.dm import filters
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import engines, orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


engines.engine_factory.configure_factory(
    db_url="mysql://test:test@127.0.0.1/test",
)

print(list(FooModel.objects.get_all()))
print(FooModel.objects.get_one(filters={"foo_field1": filters.EQ(10)}))
print(list(FooModel.objects.get_all(filters={"foo_field1": filters.GT(5)})))
print(list(FooModel.objects.get_all(filters={"foo_field1": filters.In([5, 6])})))
```

---

## 复杂表达式

```python
filter_list = filters.OR(
    filters.AND({
        "name1": filters.EQ(1),
        "name2": filters.EQ(2),
    }),
    filters.AND({
        "name2": filters.EQ(3),
    }),
)

print(FooModel.objects.get_one(filters=filter_list))
```

---

## 使用建议

- 简单情况优先使用字典形式：`{"field": filters.EQ(value)}`。
- 当逻辑条件较复杂时再使用 `AND`/`OR` 组合表达式。
- 不要在业务代码中手动解析过滤对象，应由存储或 API 层统一处理。
