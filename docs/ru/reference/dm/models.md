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

# DM-модели

Модуль: `restalchemy.dm.models`

Этот модуль содержит базовые классы и mixin-классы для моделей данных (DM) в RESTAlchemy.

---

## MetaModel и Model

### `MetaModel`

`MetaModel` — метакласс, используемый всеми DM-моделями. Он:

- Собирает определения полей, созданных через `properties.property()` и `properties.container()`.
- Объединяет свойства базовых классов.
- Отслеживает ID-свойства в `id_properties`.
- Присваивает операционное хранилище `__operational_storage__` для вспомогательных данных на уровне класса модели.

Обычно `MetaModel` не используется напрямую; вы наследуетесь от `Model` или её наследников.

### `Model`

`Model` — фундаментальный базовый класс для DM-моделей:

```python
from restalchemy.dm import models, properties, types


class Foo(models.Model):
    foo_id = properties.property(types.Integer(), id_property=True, required=True)
    name = properties.property(types.String(max_length=255), default="")
```

Основное поведение:

- Конструктор принимает именованные аргументы и передаёт их в `pour()`.
- `pour()` строит `PropertyManager` из коллекции `properties` и выполняет валидацию.
- Доступ к атрибутам проксируется в свойства:
  - `model.field` читает `properties[field].value`.
  - `model.field = value` устанавливает значение с валидацией.
- `as_plain_dict()` возвращает словарь с "плоским" представлением значений.
- Модель ведёт себя как отображение по своим свойствам (`__getitem__`, `__iter__`, `__len__`).

Обработка ошибок:

- При установке значения неверного типа выбрасывается `ModelTypeError`.
- При отсутствии обязательного поля выбрасывается `PropertyRequired`.
- При попытке изменить read-only или ID-свойство выбрасывается `ReadOnlyProperty`.

Переопределение валидации:

```python
class PositiveFoo(models.Model):
    value = properties.property(types.Integer(), required=True)

    def validate(self):
        if self.value <= 0:
            raise ValueError("value must be positive")
```

`validate()` вызывается из `pour()` после создания свойств.

---

## Работа с ID

### `ModelWithID`

`ModelWithID` расширяет `Model` для моделей с ровно одним ID-свойством:

- `get_id()` возвращает текущее значение ID-свойства.
- Операции сравнения и хеширования основаны на `get_id()`.

Если у модели нет ID-свойств или их несколько, `get_id_property()` выбрасывает `TypeError`, и логику ID нужно реализовать самостоятельно.

### `ModelWithUUID` и `ModelWithRequiredUUID`

`ModelWithUUID` определяет UUID как первичный ключ:

```python
class ModelWithUUID(ModelWithID):
    uuid = properties.property(
        types.UUID(),
        read_only=True,
        id_property=True,
        default=lambda: uuid.uuid4(),
    )
```

Пример использования:

```python
class Foo(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)

foo = Foo(value=10)
print(foo.uuid)       # авто-сгенерированный UUID
print(foo.get_id())   # то же самое, что foo.uuid
```

`ModelWithRequiredUUID` похож, но UUID должен быть задан явно, без значения по умолчанию.

---

## Операционное хранилище

### `DmOperationalStorage`

Небольшой вспомогательный класс, используемый `MetaModel` как `__operational_storage__` для каждой модели:

- `store(name, data)` — сохраняет произвольные данные по имени.
- `get(name)` — возвращает данные или выбрасывает `NotFoundOperationalStorageError`, если запрошенного ключа нет.

Пример:

```python
from restalchemy.dm import models


class Foo(models.ModelWithUUID):
    pass

Foo.__operational_storage__.store("table_name", "foos")

assert Foo.__operational_storage__.get("table_name") == "foos"
```

Обычно используется внутренними механизмами и расширениями.

---

## Распространённые mixin-классы

### `ModelWithTimestamp`

Добавляет поля `created_at` и `updated_at` с UTC-временем:

- Оба поля обязательные, read-only и используют `types.UTCDateTimeZ()`.
- `update()` автоматически обновляет `updated_at`, если модель "грязная" (или при `force=True`).

```python
class TimestampedFoo(models.ModelWithUUID, models.ModelWithTimestamp):
    value = properties.property(types.Integer(), required=True)
```

### `ModelWithProject`

Добавляет обязательное, read-only поле `project_id` типа `types.UUID()`:

```python
class ProjectResource(models.ModelWithUUID, models.ModelWithProject):
    name = properties.property(types.String(max_length=255), required=True)
```

### `ModelWithNameDesc` и `ModelWithRequiredNameDesc`

Общие поля `name` и `description`:

- `ModelWithNameDesc`:
  - `name`: строка до 255 символов, по умолчанию `""`.
  - `description`: строка до 255 символов, по умолчанию `""`.
- `ModelWithRequiredNameDesc`:
  - `name` является обязательным полем.

Полезно для большого количества сущностей с именем и описанием.

---

## Дополнительные свойства и simple view

### `CustomPropertiesMixin`

Позволяет определять дополнительные "кастомные" свойства с отдельными типами:

- `__custom_properties__`: словарь имя → тип (`types.BaseType`).
- `get_custom_properties()` возвращает пары `(name, type)`.
- `get_custom_property_type(name)` возвращает тип для заданного свойства.
- `_check_custom_property_value()` валидирует и может проверять фиксированные значения.

Обычно используется совместно с mixin-классами simple view.

### `DumpToSimpleViewMixin`

Метод `dump_to_simple_view()` конвертирует модель в структуру из простых типов Python (для JSON, OpenAPI, storage):

```python
result = model.dump_to_simple_view(
    skip=["internal_field"],
    save_uuid=True,
    custom_properties=False,
)
```

Поведение:

- Обходит `self.properties` и конвертирует каждое значение через `to_simple_type()` типа поля.
- При `save_uuid=True` UUID-поля (включая `AllowNone(UUID)`) сериализуются как строки.
- При `custom_properties=True` (или наличии `__custom_properties__`) конвертируются и кастомные свойства.

### `RestoreFromSimpleViewMixin`

Метод `restore_from_simple_view()` создаёт модель из "плоской" структуры:

```python
user = User.restore_from_simple_view(
    skip_unknown_fields=True,
    name="Alice",
    created_at="2006-01-02T15:04:05.000576Z",
)
```

Поведение:

- Нормализует имена полей (заменяет `-` на `_`).
- Опционально пропускает неизвестные поля.
- Использует `from_simple_type()` / `from_unicode()` типа свойства для конвертации.

### `SimpleViewMixin`

Удобный mixin, совмещающий оба поведения:

```python
class User(models.ModelWithUUID, models.SimpleViewMixin):
    name = properties.property(types.String(max_length=255), required=True)
```

Пример round-trip через simple view:

```python
plain = user.dump_to_simple_view()
user2 = User.restore_from_simple_view(**plain)
```

---

## Резюме

- Используйте `Model` (или её наследников) как основу для всех DM-моделей.
- Применяйте mixin-классы `ModelWithUUID`, `ModelWithTimestamp`, `ModelWithProject`, `ModelWithNameDesc` для избежания дублирования.
- Используйте simple view mixin-ы для конвертации моделей в простые структуры и обратно при интеграции с API, OpenAPI и внешними хранилищами.
