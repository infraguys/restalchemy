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

## Рекомендации

- В большинстве случаев используйте словари вида `{ "field": filters.EQ(value) }`.
- Переходите к `AND`/`OR` только для действительно сложных логических комбинаций.
- Не пытайтесь самостоятельно вычислять фильтры: это задача storage/API-слоя.
- Держите логику фильтрации рядом с кодом запросов (репозитории, сервисный слой) для лучшей читаемости.
