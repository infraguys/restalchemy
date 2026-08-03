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

# Фильтры (Filters)

Модуль: `restalchemy.dm.filters`

Фильтры описывают условия выборки для DM-моделей. Обычно они используются слоями хранения и API для построения WHERE-условий и фильтрации коллекций.

---

## Классы условий (clauses)

Все классы условий наследуются от `AbstractClause`:

- Хранят одно значение `value`.
- Реализуют сравнение и строковое представление для отладки.

Простые условия сравнения и принадлежности:

- `EQ(value)` — равно.
- `NE(value)` — не равно.
- `GT(value)` — больше.
- `GE(value)` — больше или равно.
- `LT(value)` — меньше.
- `LE(value)` — меньше или равно.
- `Is(value)` — сравнение вида `IS` (например, `IS NULL`).
- `IsNot(value)` — `IS NOT`.
- `In(value)` — принадлежность множеству.
- `NotIn(value)` — не принадлежит множеству.
- `Like(value)` — шаблонное сравнение.
- `NotLike(value)` — отрицание `Like`.
- `ContainsAll(value)` (массивы PostgreSQL) — оператор `@>`, содержит все перечисленные элементы. По HTTP: `?q=field:"a" AND field:"b"`, см. [Фильтрация коллекций по HTTP](../../how-to/api-filtering.md).
- `ContainsAny(value)` (массивы PostgreSQL) — оператор `&&`, пересекается с перечисленными элементами. По HTTP: `?q=field:"a" OR field:"b"`.
- `JSONFields(value)` (jsonb-колонки PostgreSQL) — фильтрация по ключам внутри jsonb-колонки; см. раздел [Фильтры по JSON-полям](#json-field-filters) ниже.

Пример:

```python
from restalchemy.dm import filters

f1 = filters.EQ(10)
assert str(f1) == "10"
```

---

## Классы выражений (expressions)

Выражения группируют условия логически.

- `AbstractExpression` — базовый класс.
- `ClauseList` — контейнер для нескольких условий.
- `AND(*clauses)` — логическое И над условиями/выражениями.
- `OR(*clauses)` — логическое ИЛИ.
- `NOT(*clauses)` — отрицание конъюнкции своих условий, `NOT (a AND b)`.
  Отдельный узел, а не отрицание, протолкнутое внутрь условий: `NOT (col = 1)`
  и `col <> 1` — разные фильтры, как только в игру вступает NULL.

Эти классы не вычисляются напрямую в Python; они интерпретируются слоем хранения или API и транслируются, например, в SQL.

---

## Использование фильтров с DM + storage

Пример по мотивам `examples/dm_mysql_storage.py`:

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

Здесь:

- Ключи словаря — имена полей (`"foo_field1"`).
- Значения — объекты-фильтры (`filters.EQ(10)`, `filters.GT(5)`, `filters.In([...])`).
- Слой хранения интерпретирует их и строит правильные SQL WHERE-условия.

---

## Сложные выражения

Для сложных запросов используйте `AND` и `OR`.

Пример (из `examples/dm_mysql_storage.py`):

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

Сторона хранения понимает такие вложенные выражения и строит соответствующий запрос.

---

## Фильтры по JSON-полям {#json-field-filters}

`JSONFields` фильтрует по ключам внутри jsonb-колонки PostgreSQL и поддерживает для этих ключей не только проверку на вхождение, но и условия равенства и диапазона:

```python
from restalchemy.dm import filters

# WHERE (spec->>'kind') = %s AND (spec->>'value')::bigint > %s
FooModel.objects.get_all(
    filters={"spec": filters.JSONFields({"kind": "foo", "value": filters.GT(10)})}
)
```

Каждый ключ отображения — либо простое скалярное значение (сокращённая запись для `EQ`), либо явное условие (`EQ`, `NE`, `GT`, `GE`, `LT`, `LE`, `Like`, `NotLike`, `Is`, `IsNot`). Ключи объединяются по AND. Значения приводятся к типу в генерируемом SQL исходя из их типа в Python (`bool` → `::boolean`, `int` → `::bigint`, `float` → `::double precision`; `str`/`None` приведения не требуют) — это приведение нужно точь-в-точь повторить в любом индексе, который вы создаёте (см. ниже), иначе PostgreSQL молча проигнорирует индекс.

### Индексирование jsonb-колонки с дискриминатором «kind»

`JSONFields` рассчитан на распространённую форму полиморфного JSON: колонка всегда содержит ключ-дискриминатор (по соглашению `"kind"`) плюс несколько дополнительных ключей, наличие и смысл которых определяются конкретным kind, — например, `{"kind": "totp", "period": 30}` и `{"kind": "yubiotp", "device_id": "..."}` в одной и той же колонке. Такой форме нужны два вида индексов:

1. **Сам дискриминатор индексируйте всегда** обычным индексом по выражению: по нему фильтрует любой запрос к этой колонке, и форма условия одинакова для всех kind:

   ```sql
   CREATE INDEX ix_t_spec_kind ON t ((spec->>'kind'));
   ```

2. **Для каждой пары `(kind, field)`, по которой вы реально делаете запросы, добавляйте *частичный* индекс по выражению, ограниченный этим kind**, а не индекс по имени поля на всю таблицу: смысл поля (и само его наличие) специфичны для одного kind:

   ```sql
   CREATE INDEX ix_t_spec_totp_period ON t (((spec->>'period')::bigint))
       WHERE spec->>'kind' = 'totp';
   ```

   Замеры на таблице в 2 млн строк: запрос, сочетающий дискриминатор с полем конкретного kind (`kind = 'foo' AND value > 10`), с таким частичным индексом отработал примерно вдвое быстрее, чем с одним лишь индексом по дискриминатору из пункта 1, а запрос только по дискриминатору к одному частичному индексу превратился в index-only scan и оказался примерно в 9 раз быстрее обычного индекса по дискриминатору: PostgreSQL умеет использовать `WHERE`-условие самого частичного индекса как доказательство предиката. Фильтрацию сразу по нескольким полям одного kind оформляйте одним составным частичным индексом, а не отдельным индексом на каждое поле.

   Не создавайте частичный индекс под каждую пару `(kind, field)`, которая просто существует в схеме: пока по ней нет реальных запросов, это чистые накладные расходы на запись. Добавляйте их лениво, по фактическим сценариям запросов.

GIN-индекс (`USING gin(spec)`) запросы `JSONFields` **не** ускоряет: GIN помогает операторам `@>`/`?`/`?|`/`?&`, а не сравнениям через `->>`, в которые компилируется этот фильтр, и в тестах иногда оказывался *медленнее* обычного последовательного сканирования. Он не бесплатен и на записи: сбросы pending-list дают всплески задержек на часто обновляемых jsonb-колонках. Добавляйте GIN, только если что-то ещё в приложении действительно делает запросы через containment.

---

## Рекомендации

- В большинстве случаев используйте словари вида `{ "field": filters.EQ(value) }`.
- Переходите к `AND`/`OR` только для действительно сложных логических комбинаций.
- Не пытайтесь самостоятельно вычислять фильтры: это задача storage/API-слоя.
- Держите логику фильтрации рядом с кодом запросов (репозитории, сервисный слой) для лучшей читаемости.
