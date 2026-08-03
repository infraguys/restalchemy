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

所有子句类都继承自 `AbstractClause`：

- 保存单个 `value`。
- 实现相等比较与便于调试的字符串表示。

常见的比较与集合子句：

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
- `ContainsAll(value)`（PostgreSQL 数组列）：数组 `@>`，包含给定的全部元素。HTTP 写法：`?q=field:"a" AND field:"b"`，参见[通过 HTTP 过滤集合](../../how-to/api-filtering.md)。
- `ContainsAny(value)`（PostgreSQL 数组列）：数组 `&&`，与给定元素有交集。HTTP 写法：`?q=field:"a" OR field:"b"`。
- `JSONFields(value)`（PostgreSQL jsonb 列）：对 jsonb 列内部的键进行过滤，参见下文的 [JSON 字段过滤](#json-field-filters)。

示例：

```python
from restalchemy.dm import filters

f1 = filters.EQ(10)
assert str(f1) == "10"
```

---

## 表达式（Expressions）

表达式用于组合多个子句：

- `AbstractExpression`：基类。
- `ClauseList`：子句列表。
- `AND(*clauses)`：逻辑与。
- `OR(*clauses)`：逻辑或。
- `NOT(*clauses)`：对其各子句的合取取反，即 `NOT (a AND b)`。它是独立的节点，
  而不是把取反下推到子句里：一旦涉及 NULL，`NOT (col = 1)` 与 `col <> 1` 就不是
  同一个过滤条件。

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

其中：

- 字典的键是字段名（`"foo_field1"`）。
- 字典的值是过滤子句（`filters.EQ(10)`、`filters.GT(5)`、`filters.In([...])`）。
- 存储层会解析它们并构建正确的 SQL WHERE 条件。

---

## 复杂表达式

复杂查询可以使用 `AND` 与 `OR` 表达式。

示例（来自 `examples/dm_mysql_storage.py`）：

```python
# WHERE ((`name1` = 1 AND `name2` = 2) OR (`name2` = 3))
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

存储后端能够理解这类嵌套表达式，并生成相应的查询语句。

---

## JSON 字段过滤 {#json-field-filters}

`JSONFields` 针对 PostgreSQL `jsonb` 列内部的键进行过滤，并且对这些键不仅支持包含判断，也支持相等与范围子句：

```python
from restalchemy.dm import filters

# WHERE (spec->>'kind') = %s AND (spec->>'value')::bigint > %s
FooModel.objects.get_all(
    filters={"spec": filters.JSONFields({"kind": "foo", "value": filters.GT(10)})}
)
```

映射中的每个键，要么是普通标量值（等价于 `EQ` 的简写），要么是显式子句（`EQ`、`NE`、`GT`、`GE`、`LT`、`LE`、`Like`、`NotLike`、`Is`、`IsNot`）。各个键之间以 AND 组合。生成 SQL 时会依据值的 Python 类型做类型转换（`bool` → `::boolean`，`int` → `::bigint`，`float` → `::double precision`；`str`/`None` 无需转换）——你建立的任何索引都必须完全复现这一转换（见下文），否则 PostgreSQL 会悄悄忽略该索引。

### 为以 “kind” 作判别键的 jsonb 列建立索引

`JSONFields` 面向常见的多态 JSON 形态：列中始终带有一个判别键（约定为 `"kind"`），外加若干仅对该 kind 有意义的附加键——例如同一列中既有 `{"kind": "totp", "period": 30}`，又有 `{"kind": "yubiotp", "device_id": "..."}`。这种形态需要两类索引：

1. **始终为判别键本身建立**普通表达式索引：访问该列的每个查询都会先按它过滤，而且对所有 kind 形状一致：

   ```sql
   CREATE INDEX ix_t_spec_kind ON t ((spec->>'kind'));
   ```

2. **对每个真正会被查询的 `(kind, field)` 组合，建立限定于该 kind 的*部分*表达式索引**，而不是对字段名建立全表索引：字段的含义（乃至它是否存在）都只属于某一个 kind：

   ```sql
   CREATE INDEX ix_t_spec_totp_period ON t (((spec->>'period')::bigint))
       WHERE spec->>'kind' = 'totp';
   ```

   在 200 万行的表上实测：同时使用判别键与该 kind 专有字段的查询（`kind = 'foo' AND value > 10`），使用该部分索引比仅使用第 1 步的判别键索引快约 2 倍；而仅按判别键查询时，针对单个部分索引可走 index-only scan，比普通判别键索引快约 9 倍——PostgreSQL 可以把部分索引自身的 `WHERE` 条件当作谓词成立的证明。若需同时按同一 kind 的多个字段过滤，应建立一个复合部分索引，而不是每个字段一个索引。

   不要为模式中仅仅存在的每个 `(kind, field)` 组合都建索引：在没有真实查询用到它之前，那只是纯粹的写入开销。应按实际查询模式按需添加。

GIN 索引（`USING gin(spec)`）**不会**加速 `JSONFields` 查询：GIN 优化的是 `@>`/`?`/`?|`/`?&`，而不是该过滤器所编译出的 `->>` 比较；测试中它有时甚至*慢于*顺序扫描。它在写入侧同样有代价——pending list 的刷新会让频繁更新的 jsonb 列出现写延迟尖峰。只有当应用中确实存在使用原生包含运算的查询时，才应添加 GIN。

---

## 使用建议

- 简单情况优先使用字典形式：`{"field": filters.EQ(value)}`。
- 当逻辑条件较复杂时再使用 `AND`/`OR` 组合表达式。
- 不要在业务代码中手动解析过滤对象，应由存储或 API 层统一处理。
- 把过滤逻辑放在靠近查询代码的位置（例如仓储层或服务层），以提高可读性。
