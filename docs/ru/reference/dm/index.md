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

# Справочник по Data Model (DM)

Этот раздел описывает слой Data Model (DM) в RESTAlchemy.

Слой DM отвечает за:

- Объявление доменных моделей как Python-классов.
- Определение полей, типов и правил валидации.
- Описание связей между моделями.
- Предоставление mixin-классов для распространённых шаблонов (UUID, временные метки, имя/описание и т.д.).

Слой DM реализован в следующих модулях:

- `restalchemy.dm.models`
- `restalchemy.dm.properties`
- `restalchemy.dm.relationships`
- `restalchemy.dm.types`
- `restalchemy.dm.filters`
- `restalchemy.dm.types_dynamic` (расширенные типы)
- `restalchemy.dm.types_network` (сетевые типы)

В этом справочнике основной акцент сделан на первых пяти модулях, которые используются чаще всего.

---

## Краткий обзор

Типичная DM-модель объявляется так:

```python
from restalchemy.dm import models, properties, types


class Foo(models.ModelWithUUID):
    # Integer field, required
    value = properties.property(types.Integer(), required=True)

    # Optional string with default value
    description = properties.property(types.String(max_length=255), default="")
```

Ключевые идеи:

- Вы наследуетесь от `Model` или одного из вспомогательных базовых классов (`ModelWithUUID` и др.).
- Вы используете `properties.property()` для объявления полей.
- Вы используете классы из `types.*` для описания типа и ограничений каждого поля.

Связи между моделями описываются через `relationships.relationship()`.

Фильтры (`restalchemy.dm.filters`) используются для задания условий выборки при работе со storage и API-фильтрацией.

---

## Файлы в этом разделе

- [Модели](models.md)
  - `Model`, `ModelWithID`, `ModelWithUUID`, `ModelWithTimestamp` и другие mixin-классы.
- [Свойства](properties.md)
  - Система свойств: `Property`, `IDProperty`, `PropertyCollection`, `PropertyManager`, фабрики.
- [Связи](relationships.md)
  - `relationship()`, `required_relationship()`, `readonly_relationship()`, `Relationship`, `PrefetchRelationship`.
- [Типы](types.md)
  - Скаляры, даты/время, коллекции и структурированные типы для свойств.
- [Фильтры](filters.md)
  - Классы фильтров (`EQ`, `GT`, `In` и др.) и логические выражения (`AND`, `OR`).

Вы можете найти справочник DM на каждом языке в соответствующем разделе `reference/dm/`.
