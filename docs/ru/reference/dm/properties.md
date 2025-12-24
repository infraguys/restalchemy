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

# Свойства (Properties)

Модуль: `restalchemy.dm.properties`

Свойства — это основной механизм, используемый DM-моделями для объявления полей и хранения их значений.

---

## Базовые классы

### `AbstractProperty`

Абстрактный базовый интерфейс для всех свойств:

- `value` (property): чтение/запись текущего значения.
- `set_value_force(value)`: установка значения в обход ограничений read-only и ID.
- `is_dirty()`: проверка, изменилось ли значение с момента инициализации.
- `is_prefetch()` (classmethod): участвует ли свойство в prefetch-загрузке.

### `Property`

Основная реализация для скалярных и структурированных полей.

Конструктор:

```python
Property(
    property_type,
    default=None,
    required=False,
    read_only=False,
    value=None,
    mutable=False,
    example=None,
)
```

Ключевое поведение:

- `property_type` должен быть экземпляром `types.BaseType`.
- `default` может быть значением или вызываемым объектом; в случае callable вызывается один раз.
- Если передан `value`, он перекрывает `default`.
- Если `mutable=False`, начальное значение копируется для корректного отслеживания `is_dirty()`.
- `is_required()` и `is_read_only()` описывают правила валидации.
- При неверном типе или `None` для обязательного поля выбрасываются исключения из `restalchemy.common.exceptions`.

ID-свойства представлены классом `IDProperty`, который переопределяет `is_id_property()`.

### `IDProperty`

Специализация `Property` для ID-полей:

- `is_id_property()` возвращает `True`.
- Используется совместно с `ModelWithID` / `ModelWithUUID` для идентификации первичного ключа.

---

## PropertyCreator и фабрики

### `PropertyCreator`

Лёгкая фабрика, которая хранит способ создания конкретного свойства:

- Класс свойства (`Property` или `IDProperty`).
- Экземпляр типа (`types.String()`, `types.Integer()` и т.д.).
- Позиционные и именованные аргументы для конструктора.
- Флаг `prefetch` (для связей).

Именно объекты `PropertyCreator` вы присваиваете атрибутам класса модели.

### `property()`

Основная фабрика, используемая в моделях:

```python
from restalchemy.dm import properties, types


class Foo(models.Model):
    value = properties.property(types.Integer(), required=True)
```

Аргументы:

- `property_type`: экземпляр `types.BaseType`.
- `id_property`: если `True`, используется `IDProperty`.
- `property_class`: пользовательский класс свойства (должен наследоваться от `AbstractProperty`).
- Остальные ключевые аргументы передаются в конструктор свойства (`default`, `required`, `read_only`, `mutable`, `example` и т.д.).

Возвращает:

- `PropertyCreator`, который при инициализации модели создаёт объекты `Property` / `IDProperty`.

### Удобные фабрики

- `required_property(property_type, *args, **kwargs)` — устанавливает `required=True`.
- `readonly_property(property_type, *args, **kwargs)` — устанавливает `read_only=True` и `required=True`.

Пример:

```python
class User(models.ModelWithUUID):
    email = properties.required_property(types.Email())
    created_at = properties.readonly_property(
        types.UTCDateTimeZ(),
        default=datetime.datetime.now,
    )
```

---

## Коллекции свойств и менеджер

### `PropertyCollection`

Коллекция определений свойств, используемая `MetaModel`.

- Хранит отображение имя → `PropertyCreator` (или вложенный `PropertyCollection`).
- Реализует протокол отображения (`__getitem__`, `__iter__`, `__len__`).
- `sort_properties()` сортирует свойства по имени (полезно для тестов).
- `instantiate_property(name, value=None)` создаёт конкретный экземпляр свойства.

На уровне класса `Model.properties` — это `PropertyCollection`.

### `PropertyManager`

Контейнер на уровне экземпляра модели:

- Строится на основе `PropertyCollection` и словаря значений.
- Создаёт реальные объекты свойств (или вложенные `PropertyManager` для контейнеров).
- Предоставляет `properties` (read-only отображение свойств).
- Предоставляет `value` как словарь "сырых" значений (чтение/запись).

`Model.pour()` использует `PropertyManager` для инициализации состояния модели:

```python
self.properties = properties.PropertyManager(self.properties, **kwargs)
```

Если обязательное свойство отсутствует, `PropertyManager` выбрасывает `PropertyRequired` с именем поля.

---

## Контейнеры и вложенные структуры

### `container()`

Создаёт вложенный `PropertyCollection` для группировки связанных полей:

```python
address_container = properties.container(
    city=properties.property(types.String()),
    zip_code=properties.property(types.String()),
)


class User(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)
    address = address_container
```

Во время выполнения `address` будет вложенным `PropertyManager`, и вы можете обращаться к:

```python
user.address.value["city"]
user.address.value["zip_code"]
```

Вложенные контейнеры удобны для сложных JSON-структур и OpenAPI-схем.

---

## Отслеживание изменений

И `Property`, и `Relationship` поддерживают `is_dirty()`:

- `Property` сравнивает текущее значение с начальным.
- `Relationship` сравнивает текущий связанный объект с исходным.

`Model.is_dirty()` обходит все свойства и возвращает `True`, если хотя бы одно "грязное". Это активно используется слоями хранения для решения, нужно ли выполнять обновление.

---

## Рекомендации по использованию

- Всегда используйте DM-типы (`types.String`, `types.Integer` и т.п.), а не "сырые" Python-типы.
- Помечайте ID-поля через `id_property=True` или используйте `ModelWithUUID`/`ModelWithID`.
- При возможности используйте `required_property()` и `readonly_property()` для большей читаемости.
- Применяйте `container()` для логически сгруппированных полей или вложенных JSON-структур.
