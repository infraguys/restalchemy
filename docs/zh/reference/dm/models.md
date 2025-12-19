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

# DM 模型

模块：`restalchemy.dm.models`

本模块定义 RESTAlchemy 中数据模型（DM）的基类和常用 Mixin。

---

## MetaModel 与 Model

### `MetaModel`

`MetaModel` 是所有 DM 模型的元类，它负责：

- 收集通过 `properties.property()`、`properties.container()` 声明的字段。
- 合并父类中的属性集合。
- 在 `id_properties` 中记录 ID 字段。
- 为每个模型类挂载 `__operational_storage__`（运行期存储）。

通常不直接使用 `MetaModel`，而是继承自 `Model` 或其子类。

### `Model`

`Model` 是所有 DM 模型的基础类：

```python
from restalchemy.dm import models, properties, types


class Foo(models.Model):
    foo_id = properties.property(types.Integer(), id_property=True, required=True)
    name = properties.property(types.String(max_length=255), default="")
```

主要行为：

- 构造函数接收关键字参数并传递给 `pour()`。
- `pour()` 使用 `PropertyManager` 根据 `properties` 构建实例并执行校验。
- 属性访问映射到属性系统：
  - `model.field` 读取 `properties[field].value`。
  - `model.field = value` 设置并校验值。
- `as_plain_dict()` 返回“扁平”的字典表示。
- 模型实现映射接口（`__getitem__`、`__iter__`、`__len__`）。

错误处理：

- 赋值类型不匹配时抛出 `ModelTypeError`。
- 缺少必填字段时抛出 `PropertyRequired`。
- 修改只读或 ID 字段时抛出 `ReadOnlyProperty`。

自定义校验：

```python
class PositiveFoo(models.Model):
    value = properties.property(types.Integer(), required=True)

    def validate(self):
        if self.value <= 0:
            raise ValueError("value must be positive")
```

`validate()` 在 `pour()` 之后被调用。

---

## ID 处理

### `ModelWithID`

`ModelWithID` 用于只有一个 ID 字段的模型：

- `get_id()` 返回 ID 字段的值。
- 等号与哈希基于 `get_id()`。

若模型没有或有多个 ID 字段，`get_id_property()` 会抛出 `TypeError`，此时需自定义 ID 逻辑。

### `ModelWithUUID` 与 `ModelWithRequiredUUID`

`ModelWithUUID` 定义 UUID 主键：

```python
class ModelWithUUID(ModelWithID):
    uuid = properties.property(
        types.UUID(),
        read_only=True,
        id_property=True,
        default=lambda: uuid.uuid4(),
    )
```

示例：

```python
class Foo(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)

foo = Foo(value=10)
print(foo.uuid)
print(foo.get_id())
```

`ModelWithRequiredUUID` 类似，但 UUID 需要显式传入，没有默认值。

---

## 运行期存储

### `DmOperationalStorage`

用于每个模型类的简单辅助存储：

- `store(name, data)` — 按名称保存任意数据。
- `get(name)` — 读取数据，不存在则抛出 `NotFoundOperationalStorageError`。

---

## 常用 Mixin

### `ModelWithTimestamp`

添加 `created_at` 与 `updated_at` 两个 UTC 时间字段：

- 均为必填、只读，类型为 `types.UTCDateTimeZ()`。
- `update()` 在模型“脏”（或 `force=True`）时自动刷新 `updated_at`。

### `ModelWithProject`

添加必填、只读的 `project_id` 字段（`types.UUID()`）。

### `ModelWithNameDesc` 与 `ModelWithRequiredNameDesc`

提供通用的名称与描述字段：

- `ModelWithNameDesc`：
  - `name`：最长 255 字符，默认空字符串。
  - `description`：最长 255 字符，默认空字符串。
- `ModelWithRequiredNameDesc`：
  - `name` 为必填字段。

---

## 自定义属性与 Simple View

### `CustomPropertiesMixin`

支持定义额外“自定义属性”：

- `__custom_properties__`：名称到类型（`types.BaseType`）的映射。
- `get_custom_properties()` 返回 `(name, type)` 对。
- `get_custom_property_type(name)` 返回对应类型。

### `DumpToSimpleViewMixin`

`dump_to_simple_view()` 将模型转换为简单 Python 类型的结构：

- 遍历 `self.properties` 并调用类型的 `to_simple_type()`。
- 在 `save_uuid=True` 时，UUID 字段以字符串形式保留。
- 可选地包含自定义属性。

### `RestoreFromSimpleViewMixin`

`restore_from_simple_view()` 从简单结构重建模型：

- 将字段名中的 `-` 替换为 `_`。
- 可忽略未知字段。
- 使用类型的 `from_simple_type()` / `from_unicode()` 进行转换。

### `SimpleViewMixin`

组合了上述两个 Mixin，支持简单的序列化/反序列化：

```python
class User(models.ModelWithUUID, models.SimpleViewMixin):
    name = properties.property(types.String(max_length=255), required=True)
```

---

## 小结

- 所有 DM 模型都应基于 `Model` 或其子类。
- 对于常见模式，优先使用现成的 Mixin（`ModelWithUUID`、`ModelWithTimestamp`、`ModelWithProject` 等）。
- 使用 Simple View Mixin 便于在 API、OpenAPI 或外部存储之间进行数据转换。
