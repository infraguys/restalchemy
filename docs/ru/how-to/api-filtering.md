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

# Фильтрация коллекций по HTTP

В этом руководстве описаны параметры запроса, которые понимает эндпоинт
коллекции (метод `FILTER`), и то, как они превращаются в
[фильтры DM](../reference/dm/filters.md).

Фильтрация включается на уровне ресурса:

```python
class TaggedController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        TaggedModel,
        process_filters=True,
    )
```

Без `process_filters=True` параметры передаются как есть, строками, и не
парсятся и не валидируются вовсе.

---

## Скалярные поля

Параметр, названный по имени поля, фильтрует по равенству; значение
парсится в тип поля, поэтому значение, которое тип не принимает, — это
`400`, а не сравнение, которое молча ни с чем не совпадёт:

```http
GET /v1/vms/?name=web-1          ->  EQ("web-1")
GET /v1/vms/?name=web-1&name=web-2  ->  In(["web-1", "web-2"])
```

Повтор параметра, таким образом, читается как «любое из».

---

## Поля-массивы

Поле-массив (типичный случай — `ModelWithTags` и его `tags`) ведёт себя
иначе, и на этой разнице легко споткнуться:

```http
GET /v1/tagged/?tags=env:prod
```

означает `tags = ARRAY['env:prod']` — весь массив равен этому одному
элементу. Это допустимый фильтр, но не поиск: строка с тегами
`['env:prod', 'region:eu']` под него не подойдёт.

Поиск по элементу задаётся оператором в виде суффикса имени параметра:

- `field__contains_all=a` — `field @> ARRAY['a']`, массив содержит все
  перечисленные элементы.
- `field__contains_any=a` — `field && ARRAY['a']`, массив содержит хотя бы
  один из перечисленных элементов.

Повторяйте параметр, чтобы назвать больше элементов. В отличие от
скалярного фильтра, повторы здесь — элементы одного массива, а не
альтернативы:

```http
GET /v1/tagged/?tags__contains_all=env:prod&tags__contains_all=region:eu
```

выберет строки, помеченные **обоими** тегами, а

```http
GET /v1/tagged/?tags__contains_any=env:prod&tags__contains_any=env:staging
```

— строки, помеченные **любым** из них.

Оператор едет в имени параметра, а не в значении, потому что значения
тегов сами несут пунктуацию — `owner:user:<uuid>` встречается сплошь и
рядом, — так что форма `op:value` была бы неоднозначной.

Учтите, что `ContainsAll`/`ContainsAny` компилируются в операторы массивов
PostgreSQL. На MySQL запрос будет отвергнут, когда фильтр дойдёт до слоя
хранения.

### Что отвергается

Оба случая отвечают `400`:

- оператор на поле, которое не является массивом (`?name__contains_all=x`):
  сгенерированный SQL упал бы ниже по стеку и с худшим сообщением;
- два способа отфильтровать одно поле (`?tags=a&tags__contains_all=b` или
  `contains_all` вместе с `contains_any`): фильтры хранятся по имени поля,
  поэтому второй заменил бы первый вместо того, чтобы сузить выборку.

---

## Индексы

Фильтр по массиву хорош ровно настолько, насколько хорош его индекс.
Объявляйте GIN-индекс в той же миграции, что создаёт таблицу:

```sql
CREATE INDEX idx_tagged_tags ON tagged USING GIN (tags);
```

Для селективного значения — тега, который несёт малая доля строк, а именно
так выглядит тег владельца или идентичности, — планировщик отвечает из
индекса. Для значения, которое есть почти у каждой строки, он пойдёт по
первичному ключу и применит тег как фильтр; под `LIMIT` это более дешёвый
план, а не потерянный индекс.

---

## Фильтрация вместе с пагинацией

Пагинация складывается с фильтрами: граница курсора добавляется через AND
к тому, что задал вызывающий, и дальше они едут вместе.

```http
GET /v1/tagged/?tags__contains_all=env:prod&page_limit=50
```

Селективный случай остаётся на GIN-индексе, а курсор применяется как
обычный фильтр к строкам, которые индекс вернул.

---

## Кастомные свойства

Фильтры по кастомным (не хранимым) свойствам применяются в Python уже
после запроса, и там поддержаны только `EQ` и `In` — всё остальное,
включая операторы массивов, даёт `400`.

---

## См. также

- [Справочник по фильтрам](../reference/dm/filters.md) — сами классы
  клауз, включая `JSONFields` для колонок `jsonb`.
- [Справочник по моделям](../reference/dm/models.md) — `ModelWithTags`.
- [Базовый CRUD](api-basic-crud.md) — откуда берётся `process_filters`.
