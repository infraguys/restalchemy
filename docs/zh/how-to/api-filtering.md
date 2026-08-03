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

数组字段（最常见的就是 `ModelWithTags` 及其 `tags`）的行为不同，而且这个差别
很容易踩坑：

```http
GET /v1/tagged/?tags=env:prod
```

的含义是 `tags = ARRAY['env:prod']`——整个数组等于这一个元素。这是合法的过滤
条件，但它不是搜索：标签为 `['env:prod', 'region:eu']` 的行并不匹配。

按元素搜索正是下面的过滤表达式要解决的事——`?q=tags:"env:prod"`——并没有哪个
字段参数能做到这一点。原因出在取值上：一个标签长得像
`owner:user:<uuid>`，标点都在里面，而一个取值本身就带分隔符的参数没法再额外
承载一个运算符。表达式可以，因为它有引号。

---

## 过滤表达式

上面这些参数只能表达「若干相等条件的 AND」，别的说不了。当这不够用时——
需要 OR、分组、取反、区间——集合端点还接受一个表达式，语法是
[AIP-160](https://google.aip.dev/160) 的一个子集，放在单个参数里：

```http
GET /v1/vms/?q=name = "web-1" AND size > 10
GET /v1/vms/?q=tags:"env:prod" OR tags:"env:staging"
GET /v1/vms/?q=NOT (state = error) AND created_at >= "2026-07-01T00:00:00Z"
```

参数默认叫 `q`。凡是启用了该语言的地方，这个名字都会从字段名空间中被拿走，
因此当资源本身有一个名为 `q` 的字段时，就把参数改名——或者关掉该语言，参数
便恢复成原来的含义：

```python
class VmController(controllers.BaseResourceController):
    __filter_param__ = "filter"   # 传 None 则关闭该语言
```

### 运算符

| 写法 | 对应 | |
|---|---|---|
| `name = "web-1"` | `EQ` | |
| `name != "web-1"` | `NE` | |
| `size > 10`、`>=`、`<`、`<=` | `GT`、`GE`、`LT`、`LE` | |
| `name = null` | `Is(None)` | `!= null` 得到 `IsNot(None)` |
| `tags:"env:prod"` | `ContainsAll` | 数组含有该元素 |
| `description:*` | `IsNot(None)` | 该字段有值 |
| `spec.kind = "totp"` | `JSONFields` | `jsonb` 列内的某一个键 |
| `AND` `OR` `NOT` `(...)` | `AND` `OR` `NOT` | 关键字必须大写 |

有两点经常让人意外，都继承自 AIP-160。

`OR` 的结合力**强于** `AND`：`a = 1 OR b = 2 AND c = 3` 读作
`(a = 1 OR b = 2) AND c = 3`。拿不准就加括号。

两个限制之间的空白就是隐式的 `AND`，所以 `name = web-1 size > 10` 是一个
合取式。

### 引号

带有 `:`、`.` 或空格的值必须加引号，否则其中的标点会被当作更多语法读掉：

```http
?q=tags:"env:prod"                       # 正确
?q=tags:env:prod                         # 400——第二个 : 是运算符
?q=created_at >= "2026-07-01T00:00:00Z"
```

不加引号时，`null`、`true`、`false` 和 `*` 是这门语言的字面量；加了引号就
只是这几个字符串。

### 全部，或任一

没有哪个运算符专门表示 `ContainsAny`，也不需要有。`tags:"a"` 就是
`tags @> ARRAY['a']`，布尔运算符已经把差别说清楚了：

```http
?q=tags:"env:prod" AND tags:"region:eu"    ->  tags @> ARRAY[...]   两者都有
?q=tags:"env:prod" OR tags:"env:staging"   ->  tags && ARRAY[...]   任一即可
```

同一字段上的多个条件会合并成单个数组运算符，因此两种写法都只走一次索引，
而不是每个元素走一次。`name = a OR name = b` 也照此合并为
`name = ANY(...)`。

合并绝不会改变表达式所表达的意思。多元素的 `@>` 并不等于这些元素的并集，
因此一个已被 `AND` 拓宽的包含判断，在随后用 `OR` 连接时会保留自己的运算符：

```http
?q=(tags:"a" AND tags:"b") OR tags:"c"   ->  tags @> ARRAY['a','b'] OR tags @> ARRAY['c']
```

正是这种合并解释了为什么查询参数那套需要两个运算符名字，而表达式一个都不
需要：参数列表里既没有 AND 也没有 OR 来承载这个差别。

### 与字段参数一起使用

两者以 AND 结合，可以随意混用：

```http
GET /v1/vms/?state=active&q=tags:"env:prod" OR tags:"env:staging"
```

### 表达式在哪些情况下会被拒绝

下列每一种都是 `400`，绝不会变成一个悄悄做了别的事的过滤条件：

- 资源没有的字段，或该字段类型不接受的值；
- 资源在响应中隐藏的字段——通过 `hidden_fields`，或对 `FILTER` 方法设置
  `Permissions.HIDDEN`。拿一个 API 从不返回的字段做比较，等于一次一个比特
  地把它交出去，因此隐藏字段的回答与不存在的字段完全一致。同一条规则也适用
  于字段参数（`?secret=x`）以及 `sort_key`——后者会按一个它从不展示的值给
  集合排序；
- 表达式里出现了自定义属性（见下文）；
- 存储方言无法编译的运算符——`:` 和 `spec.kind` 仅限 PostgreSQL；
- 一次请求里出现多个 `q`：该用 AND 还是 OR 把它们连起来，请求里并没有说；
- 节点超过 100 个、嵌套深于 8 层，或长度超过 4096 个字符的表达式——上限由
  控制器上的 `__filter_max_nodes__`、`__filter_max_depth__` 与
  `__filter_max_length__` 决定，之所以要有它们，是因为过滤字符串属于不可信
  输入。长度是最先检查的：另外两项要在解析过程中才计数，而解析的第一步就是
  扫描整个字符串。

有意不支持的部分：函数（`f(x)`）、把裸字面量当作跨字段的模糊搜索、用 `-`
作为 `NOT` 的同义词、`=` 中的通配符、字段与字段比较，以及深于一层的键路径
遍历。

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
GET /v1/tagged/?project_id=<uuid>&page_limit=50
```

选择性高的情形仍然走 GIN 索引，游标则作为普通过滤条件作用于索引返回的行。

表达式的分页方式相同：游标依据字段参数构建，表达式紧随其后以 AND 附加：

```http
GET /v1/tagged/?q=tags:"env:prod"&page_limit=50&page_marker=<uuid>
```

每一页都要带上同一个表达式。游标只有相对于签发它时的那组过滤条件才有意义；
翻页途中改变过滤条件会漏掉或重复行。另外请留意，keyset 分页依赖 `ORDER BY`
背后的索引，跨多个字段的 `OR` 可能让规划器离开该索引——能用字段参数缩小范围
的地方就尽量用。

---

## 自定义属性

对自定义（非存储）属性的过滤是在查询之后于 Python 中完成的，那里只支持 `EQ`
和 `In`——其他任何条件，包括数组运算符，都会得到 `400`。

表达式参数完全够不到它们。它们是在查询已经返回的行上过滤的，而表达式无法被
拆成「存储的一半」和「Python 的一半」：`stored = 1 OR custom = 2` 没有地方可
以求值。在 `q` 里提到这样的属性会得到 `400`；`?custom=2` 依然可用。

---

## 另请参阅

- [过滤器参考](../reference/dm/filters.md) — 各个 clause 类本身，包括用于
  `jsonb` 列的 `JSONFields`。
- [模型参考](../reference/dm/models.md) — `ModelWithTags`。
- [基础 CRUD](api-basic-crud.md) — `process_filters` 的来源。
