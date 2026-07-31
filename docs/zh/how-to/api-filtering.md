<!--
Copyright 2026 Genesis Corporation

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

# 通过 HTTP 过滤集合

本指南介绍集合端点（`FILTER` 方法）能识别的查询参数，以及它们如何变成
[DM 过滤器](../reference/dm/filters.md)。

过滤按资源启用：

```python
class TaggedController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        TaggedModel,
        process_filters=True,
    )
```

若不设置 `process_filters=True`，参数将以原始字符串原样传入，既不解析也不
校验。

---

## 标量字段

以字段命名的参数按相等过滤；参数值会被解析为该字段的类型，因此类型无法接受的
值会得到 `400`，而不是一个悄无声息、什么都匹配不到的比较：

```http
GET /v1/vms/?name=web-1          ->  EQ("web-1")
GET /v1/vms/?name=web-1&name=web-2  ->  In(["web-1", "web-2"])
```

因此，重复同一个参数读作“其中任意一个”。

---

## 数组字段

数组字段（常见的就是 `ModelWithTags` 及其 `tags`）行为不同，这个差别很容易
踩坑：

```http
GET /v1/tagged/?tags=env:prod
```

表示 `tags = ARRAY['env:prod']`，即整个数组等于这一个元素。它是合法的过滤
条件，但不是搜索：带有 `['env:prod', 'region:eu']` 标签的行并不匹配。

按元素搜索要用以参数名后缀形式给出的运算符：

- `field__contains_all=a` — `field @> ARRAY['a']`，数组包含列出的全部元素。
- `field__contains_any=a` — `field && ARRAY['a']`，数组至少包含列出的一个
  元素。

重复该参数即可列出更多元素。与标量过滤不同，这里的重复是同一个数组的多个
元素，而不是多个可选项：

```http
GET /v1/tagged/?tags__contains_all=env:prod&tags__contains_all=region:eu
```

匹配**同时**带这两个标签的行，而

```http
GET /v1/tagged/?tags__contains_any=env:prod&tags__contains_any=env:staging
```

匹配带**其中任一**标签的行。

运算符放在参数名而不是参数值里，是因为取值本身就带标点——`owner:user:<uuid>`
是很常见的形式——所以 `op:value` 这种写法会产生歧义。

请注意，`ContainsAll`/`ContainsAny` 会编译为 PostgreSQL 的数组运算符。在
MySQL 上，过滤条件到达存储层时请求会被拒绝。

### 哪些写法会被拒绝

以下两种都返回 `400`：

- 在非数组字段上使用运算符（`?name__contains_all=x`）：生成的 SQL 只会在更
  下层失败，报错信息更糟；
- 对同一字段使用两种过滤方式（`?tags=a&tags__contains_all=b`，或
  `contains_all` 与 `contains_any` 同时出现）：过滤条件按字段名存放，后者会
  替换前者，而不是进一步收窄结果。

---

## 索引

数组过滤的效果取决于索引。请在创建表的那个迁移里声明 GIN 索引：

```sql
CREATE INDEX idx_tagged_tags ON tagged USING GIN (tags);
```

对于选择性高的取值——只有少部分行携带的标签，例如归属或身份标签——规划器会
走索引。对于几乎每行都有的取值，它会改走主键并把标签当作过滤条件；在
`LIMIT` 之下这是更划算的执行计划，而不是索引失效。

---

## 与分页一起过滤

分页与过滤可以叠加：游标的边界会以 AND 附加到调用方给出的过滤条件上，二者
一同下推。

```http
GET /v1/tagged/?tags__contains_all=env:prod&page_limit=50
```

选择性高的情形仍然走 GIN 索引，游标则作为普通过滤条件作用于索引返回的行。

---

## 自定义属性

对自定义（非存储）属性的过滤是在查询之后于 Python 中完成的，那里只支持 `EQ`
和 `In`——其他任何条件，包括数组运算符，都会得到 `400`。

---

## 另请参阅

- [过滤器参考](../reference/dm/filters.md) — 各个 clause 类本身，包括用于
  `jsonb` 列的 `JSONFields`。
- [模型参考](../reference/dm/models.md) — `ModelWithTags`。
- [基础 CRUD](api-basic-crud.md) — `process_filters` 的来源。
