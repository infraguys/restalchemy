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

# 类型（Types）

模块：`restalchemy.dm.types`

DM 类型用于描述属性可以接受的值，以及如何在 Python 对象与简单类型（JSON、OpenAPI、存储格式等）之间进行转换。

所有类型均继承自 `BaseType`。

---

## BaseType

### `BaseType`

基础接口：

- `validate(value)`：检查值是否合法。
- `to_simple_type(value)`：转换为简单类型（字符串、数字、dict、list 等）。
- `from_simple_type(value)`：从简单类型还原。
- `from_unicode(value)`：从字符串解析。
- `to_openapi_spec(prop_kwargs)`：生成 OpenAPI 片段。

许多具体类型基于 `BasePythonType`，它包装了 `int`、`str` 之类的 Python 类型。

---

## 标量类型

### `Boolean`

- 包装 `bool`。
- `from_simple_type()` 接受任意真值/假值，`from_unicode()` 接受字符串形式。

### `String`

- 包装 `str`，并带有长度限制。
- 参数：`min_length`、`max_length`。
- `to_openapi_spec()` 会补充 `minLength`/`maxLength`。

常见子类：

- `Email`：校验邮箱地址（可选做可投递性检查）。

### `Integer`

- 包装 `int`，带 `min_value` 与 `max_value`。
- `Int8`、`Int16` 等是特化变体。

### `Float`

- 包装 `float`，带取值范围。

### `Decimal`

- 包装 `decimal.Decimal`，可选 `max_decimal_places`。
- 以字符串形式序列化与反序列化，避免精度丢失。

### `UUID`

- 包装 `uuid.UUID`。
- 序列化为字符串形式。

### `Enum`

- 将取值限定于给定的集合。

示例：

```python
from restalchemy.dm import types

status_type = types.Enum(["pending", "active", "disabled"])
```

在属性中使用：

```python
status = properties.property(status_type, default="pending")
```

---

## 日期与时间类型

### `UTCDateTime`（已不推荐）与 `UTCDateTimeZ`

- 两者都包装 `datetime.datetime`。
- `UTCDateTimeZ` 强制 `tzinfo == datetime.timezone.utc`，推荐使用。
- 序列化为 MySQL / 类 RFC3339 格式的字符串。

### `TimeDelta`

- 包装 `datetime.timedelta`。
- 序列化为浮点数表示的秒数。

### `DateTime`

- 旧式时间戳类型，序列化为 Unix 时间戳。

---

## 集合类型

### `List` 与 `TypedList`

- `List` 校验值是否为 Python 列表。
- `TypedList(nested_type)` 保证每个元素都符合 `nested_type`。

示例：

```python
from restalchemy.dm import types


tags_type = types.TypedList(types.String(max_length=32))
```

### `Dict` 与结构化字典

- `Dict` 校验值是否为键为字符串的 `dict`。
- `TypedDict(nested_type)` 要求所有值都符合 `nested_type`。

基于模式的字典：

- `SoftSchemeDict(scheme)`：键是模式的子集。
- `SchemeDict(scheme)`：必须与模式完全一致。

示例：

```python
from restalchemy.dm import types


settings_scheme = {
    "retries": types.Integer(min_value=0),
    "timeout": types.Float(min_value=0.0),
}

settings_type = types.SoftSchemeDict(settings_scheme)
```

在属性中使用：

```python
settings = properties.property(settings_type, default=dict)
```

---

## 可空与包装类型

### `AllowNone(nested_type)`

- 允许值为 `None`，或符合 `nested_type` 的合法值。
- 当值不为 `None` 时，`to_simple_type()` 与 `from_simple_type()` 会透传给 `nested_type`。
- `to_openapi_spec()` 会增加 `nullable: true`。

示例：

```python
maybe_uuid = types.AllowNone(types.UUID())

uuid_or_none = properties.property(maybe_uuid)
```

---

## 正则与 URL 类型

### `BaseRegExpType` 与 `BaseCompiledRegExpTypeFromAttr`

基于正则表达式的底层基类。

具体类型包括：

- `Uri`：校验以 UUID 结尾的 URI 路径。
- `Mac`：校验 MAC 地址。
- `Hostname`（已不推荐）：参见 `types_network`。
- `Url`：HTTP/FTP URL 校验器。

这些类型适用于网络相关的资源标识符。

---

## 动态与网络类型

更多特化类型位于：

- `restalchemy.dm.types_dynamic`
- `restalchemy.dm.types_network`

例如：

- 更完善的主机名、IP 网络、CIDR 范围。
- 运行时定义模式的动态结构。

本参考不逐一列举全部类型，但使用模式始终相同：

1. 实例化类型。
2. 在 `properties.property()` 中使用它。
3. 由 DM 层负责校验与转换。

---

## 使用建议

- 优先使用 DM 类型（`types.String`、`types.Integer` 等）而不是 Python 原生类型：它们同时承载校验规则与 OpenAPI 元数据。
- 使用 `AllowNone`，而不是在业务逻辑里手工放行 `None`。
- 使用 `Enum` 表达有限值集合。
- 对于复杂 JSON 结构，优先选择 `SoftSchemeDict`、`SchemeDict`、`TypedDict`。
