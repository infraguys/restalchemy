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

# Связи (Relationships)

Модуль: `restalchemy.dm.relationships`

Связи описывают отношения между DM-моделями.

---

## Фабрики связей

### `relationship(property_type, *args, **kwargs)`

Основная фабрика для объявления связей внутри DM-моделей.

Аргументы:

- `property_type`: класс связанной модели (наследник `models.Model`).
- Позиционные `*args`: как правило, классы моделей для дополнительной валидации.
- Ключевые аргументы:
  - `prefetch`: если `True`, используется класс `PrefetchRelationship`.
  - `required`, `read_only`, `default` и др.

Под капотом функция:

- Проверяет, что все позиционные аргументы — классы DM-моделей.
- Выбирает класс свойства:
  - `PrefetchRelationship`, если `prefetch=True`.
  - `Relationship` в остальных случаях.
- Делегирует в `properties.property()` с указанным `property_class`.

### `required_relationship(property_type, *args, **kwargs)`

Аналогично `relationship()`, но устанавливает `required=True`.

### `readonly_relationship(property_type, *args, **kwargs)`

Аналогично `required_relationship()`, но дополнительно устанавливает `read_only=True`.

---

## Классы связей

### `Relationship`

Свойство, представляющее одну связанную модель.

Параметры конструктора аналогичны скалярным `Property`, но `property_type` — класс модели:

- `property_type`: класс DM-модели.
- `default`, `required`, `read_only`, `value`.

Поведение:

- Принимает `None` или экземпляр `property_type`.
- Учитывает флаги `required` и `read_only`.
- Отслеживает `is_dirty()` через сравнение текущего значения с исходным.
- `get_property_type()` возвращает класс связанной модели.

При передаче значения неправильного типа выбрасывается `TypeError`.

### `PrefetchRelationship`

Подкласс `Relationship`, используемый при `prefetch=True`:

- Переопределяет `is_prefetch()` (возвращает `True`).
- В остальном ведёт себя как `Relationship`.

Флаг prefetch обычно учитывается слоями хранения / API для оптимизации загрузки.

---

## Пример: связь один-ко-многим через DM + API

Упрощённая версия связки Foo/Bar из примеров:

```python
from restalchemy.dm import models, properties, relationships, types


class FooModel(models.ModelWithUUID):
    value = properties.property(types.Integer(), required=True)


class BarModel(models.ModelWithUUID):
    name = properties.property(types.String(max_length=10), required=True)
    foo = relationships.relationship(FooModel)
```

Использование:

```python
foo = FooModel(value=10)
bar = BarModel(name="test", foo=foo)

assert bar.foo is foo
```

В сочетании со storage (см. примеры DM + SQL) связи используются для выражения внешних ключей и join-ов.

---

## Пример: обязательная и read-only связь

```python
class ReadOnlyBar(models.ModelWithUUID):
    foo = relationships.readonly_relationship(FooModel)
```

- Связь `foo` всегда должна быть установлена (required).
- Её нельзя изменить после инициализации (read-only), если не использовать низкоуровневый `set_value_force()`.

---

## Рекомендации

- Используйте связи для DM-уровневого описания отношений между сущностями; реальные внешние ключи и join-ы обрабатываются слоем хранения.
- Старайтесь делать связи простыми: одно поле — одна логическая связь.
- Применяйте `prefetch=True` только там, где действительно нужно подсказать слоям хранения/API поведение по предварительной загрузке.
