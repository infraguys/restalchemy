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

# 属性（Properties）

模块：`restalchemy.dm.properties`

属性是 DM 模型定义字段与管理值的核心机制。

---

## 基础类

### `AbstractProperty`

所有属性的抽象基类：

- `value`：当前值。
- `set_value_force(value)`：强制设置值，绕过只读/ID 限制。
- `is_dirty()`：判断值是否自初始化以来发生变化。
- `is_prefetch()`：是否用于预取（prefetch）。

### `Property`

通用属性实现，用于标量和结构化字段。

构造函数：

```python
Property(
    property_type,
    default=None,
    required=False,
    read_only=False,
    value=None,
    mutable=False,
    example=None,
)
```

关键点：

- `property_type` 必须是 `types.BaseType` 实例。
- `default` 可以是值或可调用对象；可调用对象会在初始化时执行一次。
- 若传入 `value`，则优先于 `default`。
- `mutable=False` 时，初始值会被拷贝，以便正确实现 `is_dirty()`。
- 无效值会触发 `restalchemy.common.exceptions` 中的异常。

### `IDProperty`

用于 ID 字段的专用属性：

- `is_id_property()` 返回 `True`。
- 与 `ModelWithID`、`ModelWithUUID` 搭配使用。

---

## PropertyCreator 与工厂函数

### `PropertyCreator`

保存创建具体属性实例所需的信息：

- 属性类（`Property` 或 `IDProperty`）。
- DM 类型实例（如 `types.String()`、`types.Integer()`）。
- 构造函数参数。
- `prefetch` 标志。

在模型类定义中，真正赋值给类属性的是 `PropertyCreator`。

### `property()`

模型中最常用的工厂函数：

```python
from restalchemy.dm import properties, types


class Foo(models.Model):
    value = properties.property(types.Integer(), required=True)
```

参数：

- `property_type`：`types.BaseType` 实例。
- `id_property`：若为 `True`，使用 `IDProperty`。
- `property_class`：自定义属性类，必须继承 `AbstractProperty`。
- 其它关键字参数传递给属性构造函数（`default`、`required`、`read_only`、`mutable`、`example` 等）。

辅助工厂函数：

- `required_property(...)`：自动设置 `required=True`。
- `readonly_property(...)`：自动设置 `read_only=True` 且 `required=True`。

---

## PropertyCollection 与 PropertyManager

### `PropertyCollection`

在类级别上保存字段定义：

- 映射 字段名 → `PropertyCreator` 或嵌套 `PropertyCollection`。
- 实现映射协议。
- `sort_properties()` 按名称排序（主要用于测试）。
- `instantiate_property(name, value=None)` 创建具体属性实例。

### `PropertyManager`

在实例级别管理属性：

- 根据 `PropertyCollection` 与初始值构建实际属性对象。
- `properties`：只读映射 字段名 → 属性实例。
- `value`：字段名到“原始值”的字典（可读写）。

`Model.pour()` 通过 `PropertyManager` 初始化模型内部状态。

---

## 容器与嵌套结构

### `container()`

创建嵌套属性集合，用于一组相关字段：

```python
address_container = properties.container(
    city=properties.property(types.String()),
    zip_code=properties.property(types.String()),
)


class User(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)
    address = address_container
```

运行时 `address` 是一个嵌套的 `PropertyManager`：

```python
user.address.value["city"]
user.address.value["zip_code"]
```

---

## 修改跟踪（Dirty Tracking）

`Property` 与 `Relationship` 都支持 `is_dirty()`：

- `Property` 比较当前值与初始值。
- `Relationship` 比较当前关联对象与初始值。

`Model.is_dirty()` 遍历所有字段，只要有一个字段“脏”，就返回 `True`。

---

## 使用建议

- 在属性中尽量使用 DM 类型（`types.String`、`types.Integer` 等），而不是原生 Python 类型。
- 使用 `id_property=True` 或 `ModelWithUUID`/`ModelWithID` 明确标记主键字段。
- 根据需要使用 `required_property()`、`readonly_property()` 提升可读性。
- 使用 `container()` 表达逻辑分组或嵌套 JSON 结构。
