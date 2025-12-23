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

---

## 标量类型

- `Boolean`：布尔类型。
- `String`：字符串类型，支持 `min_length`、`max_length` 限制。
  - 子类 `Email`：用于邮箱校验。
- `Integer`：整数类型，带 `min_value`、`max_value`。
- `Float`：浮点数类型。
- `Decimal`：`decimal.Decimal`，支持小数位数限制。
- `UUID`：`uuid.UUID`。
- `Enum`：限定于一组固定值。

示例：

```python
status_type = types.Enum(["pending", "active", "disabled"])
status = properties.property(status_type, default="pending")
```

---

## 日期与时间类型

- `UTCDateTime`（已不推荐）与 `UTCDateTimeZ`：用于 UTC `datetime`。
- `TimeDelta`：持续时间，序列化为秒数。
- `DateTime`：旧式时间戳类型，序列化为 Unix 时间戳。

---

## 集合类型

- `List`：列表。
- `TypedList(nested_type)`：元素类型受 `nested_type` 约束的列表。
- `Dict`：键为字符串的字典。
- `TypedDict(nested_type)`：值类型受 `nested_type` 约束的字典。
- `SoftSchemeDict(scheme)` / `SchemeDict(scheme)`：基于模式的结构化字典。

示例：

```python
settings_scheme = {
    "retries": types.Integer(min_value=0),
    "timeout": types.Float(min_value=0.0),
}

settings_type = types.SoftSchemeDict(settings_scheme)
settings = properties.property(settings_type, default=dict)
```

---

## 可空与包装类型

### `AllowNone(nested_type)`

允许值为 `None` 或符合 `nested_type`：

```python
maybe_uuid = types.AllowNone(types.UUID())

uuid_or_none = properties.property(maybe_uuid)
```

在 OpenAPI 中会增加 `nullable: true`。

---

## 正则与 URL 类型

基于正则表达式的基础类型：`BaseRegExpType`、`BaseCompiledRegExpTypeFromAttr`。

具体类型包括：

- `Uri`：匹配以 UUID 结尾的路径。
- `Mac`：MAC 地址。
- `Hostname`（已不推荐）：参见 `types_network`。
- `Url`：HTTP/FTP URL。

---

## 动态与网络类型

`restalchemy.dm.types_dynamic` 与 `restalchemy.dm.types_network` 中提供更多高级类型：

- 主机名、IP 网络、CIDR 范围等。
- 运行时定义模式的动态结构。

使用模式始终相同：

1. 实例化类型。
2. 在 `properties.property()` 中使用它。
3. 由 DM 层负责校验与转换。

---

## 使用建议

- 在属性中尽量使用 DM 类型，而不是直接使用 Python 原生类型。
- 使用 `AllowNone` 明确表示字段可以为 `None`。
- 使用 `Enum` 表达有限值集合。
- 对于复杂 JSON 结构，优先选择 `SoftSchemeDict`、`SchemeDict`、`TypedDict`。
