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

# 关系（Relationships）

模块：`restalchemy.dm.relationships`

关系用于连接不同的 DM 模型。

---

## 关系工厂函数

### `relationship(property_type, *args, **kwargs)`

在 DM 模型中声明关系的主要入口。

参数：

- `property_type`：目标模型类（继承自 `models.Model`）。
- `*args`：通常也是模型类，用于额外校验。
- `**kwargs`：
  - `prefetch`：为 `True` 时使用 `PrefetchRelationship`。
  - `required`、`read_only`、`default` 等。

### `required_relationship(property_type, *args, **kwargs)`

等价于 `relationship()`，但自动设置 `required=True`。

### `readonly_relationship(property_type, *args, **kwargs)`

在 `required_relationship()` 基础上再设置 `read_only=True`。

---

## 关系类

### `Relationship`

表示一个“指向单个模型实例”的属性。

行为：

- 值可以是 `None` 或 `property_type` 的实例。
- 遵守 `required` 和 `read_only` 规则。
- `is_dirty()` 基于初始值判断是否发生变更。
- `get_property_type()` 返回目标模型类型。

### `PrefetchRelationship`

`Relationship` 的子类：

- `is_prefetch()` 返回 `True`。
- 其它行为与 `Relationship` 相同。

存储或 API 层可以根据 `is_prefetch()` 决定是否进行预取（eager loading）。

---

## 示例：一对多关系

简化自示例中的 Foo/Bar：

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)


class BarModel(models.ModelWithUUID):
    name = properties.property(types.String(max_length=10), required=True)
    foo = relationships.relationship(FooModel)
```

使用：

```python
foo = FooModel(value=10)
bar = BarModel(name="test", foo=foo)

assert bar.foo is foo
```

结合 Storage（参见 DM+SQL 示例），可以将关系映射到外键与 join。

---

## 示例：必填且只读的关系

```python
class ReadOnlyBar(models.ModelWithUUID):
    foo = relationships.readonly_relationship(FooModel)
```

- `foo` 关系为必填。
- 初始化后不可修改（除非使用底层 `set_value_force()`）。

---

## 使用建议

- 将 Relationships 用于“模型层”的关系建模，具体外键和 join 由存储层处理。
- 一个字段表示一条清晰的关系，不要在一个字段中混合多种含义。
- 仅在确实需要时使用 `prefetch=True` 提示预取行为。
