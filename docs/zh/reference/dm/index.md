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

# Data Model (DM) 参考

本节介绍 RESTAlchemy 中的 Data Model (DM) 层。

DM 层负责：

- 将领域模型定义为 Python 类。
- 定义字段、类型和校验规则。
- 描述模型之间的关系。
- 提供常见模式的 Mixin（例如 UUID、时间戳、名称/描述等）。

DM 层主要由以下模块组成：

- `restalchemy.dm.models`
- `restalchemy.dm.properties`
- `restalchemy.dm.relationships`
- `restalchemy.dm.types`
- `restalchemy.dm.filters`
- `restalchemy.dm.types_dynamic` （高级类型）
- `restalchemy.dm.types_network` （网络相关类型）

本参考文档重点介绍前五个模块，它们在日常使用中最常见。

---

## 快速概览

一个典型的 DM 模型如下：

```python
from restalchemy.dm import models, properties, types


class Foo(models.ModelWithUUID):
    # Integer field, required
    value = properties.property(types.Integer(), required=True)

    # Optional string with default value
    description = properties.property(types.String(max_length=255), default="")
```

关键点：

- 继承自 `Model` 或辅助基类（如 `ModelWithUUID`）。
- 使用 `properties.property()` 定义字段。
- 使用 `types.*` 类型指定字段的类型和约束。

模型之间的关系通过 `relationships.relationship()` 定义。

过滤条件（`restalchemy.dm.filters`）用于 Storage 和 API 层构建查询条件。

---

## 本节包含的文件

- [模型](models.md)
  - `Model`、`ModelWithID`、`ModelWithUUID`、`ModelWithTimestamp` 以及其它 Mixin。
- [属性](properties.md)
  - 属性系统：`Property`、`IDProperty`、`PropertyCollection`、`PropertyManager`、工厂函数等。
- [关系](relationships.md)
  - `relationship()`、`required_relationship()`、`readonly_relationship()`、`Relationship`、`PrefetchRelationship`。
- [类型](types.md)
  - 标量、日期时间、集合和结构化类型。
- [过滤器](filters.md)
  - 过滤子句（`EQ`、`GT`、`In` 等）和逻辑表达式（`AND`、`OR`）。

这些文件在四种语言下结构完全一致：

你可以在每种语言对应的 `reference/dm/` 部分找到 DM 参考。
