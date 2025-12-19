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

# Типы (Types)

Модуль: `restalchemy.dm.types`

Типы DM описывают допустимые значения для свойств и то, как значения конвертируются в простые типы (для JSON, OpenAPI, storage и т.д.).

Все типы наследуются от `BaseType`.

---

## BaseType

### `BaseType`

Базовый интерфейс для всех DM-типов:

- `validate(value) -> bool`: проверяет допустимость значения.
- `to_simple_type(value)`: конвертирует значение в простой Python-тип (строка, число, dict, list и т.п.).
- `from_simple_type(value)`: обратная конвертация из простого типа.
- `from_unicode(value)`: разбор строкового представления.
- `to_openapi_spec(prop_kwargs)`: формирует фрагмент схемы OpenAPI.

Многие конкретные типы основаны на `BasePythonType`, который оборачивает Python-типы (`int`, `str` и др.).

---

## Скалярные типы

### `Boolean`

- Оборачивает `bool`.
- Поддерживает конвертацию из простых значений и строковых представлений.

### `String`

- Оборачивает `str` с ограничениями по длине.
- Параметры: `min_length`, `max_length`.
- `to_openapi_spec()` добавляет `minLength`/`maxLength`.

Подклассы:

- `Email` — валидирует email-адреса (при желании — с проверкой доставляемости).

### `Integer`

- Оборачивает `int` с `min_value` и `max_value`.
- Есть специализированные варианты (`Int8` и т.п.).

### `Float`

- Оборачивает `float` с границами.

### `Decimal`

- Оборачивает `decimal.Decimal` с опциональным `max_decimal_places`.
- Сохраняет точность, сериализуя в строку.

### `UUID`

- Оборачивает `uuid.UUID`.
- Сериализует в строку.

### `Enum`

- Ограничивает значение фиксированным набором допустимых значений.

Пример:

```python
from restalchemy.dm import types

status_type = types.Enum(["pending", "active", "disabled"])
```

Использование в свойстве:

```python
status = properties.property(status_type, default="pending")
```

---

## Дата и время

### `UTCDateTime` (устаревший) и `UTCDateTimeZ`

- Оба оборачивают `datetime.datetime`.
- `UTCDateTimeZ` требует `tzinfo == datetime.timezone.utc` и рекомендуется к использованию.
- Сериализуют в строку в формате MySQL / RFC3339-подобном.

### `TimeDelta`

- Оборачивает `datetime.timedelta`.
- Сериализует в количество секунд (float).

### `DateTime`

- Устаревший тип, сериализующийся в Unix timestamp.

---

## Коллекции

### `List` и `TypedList`

- `List` проверяет, что значение — список.
- `TypedList(nested_type)` проверяет, что каждый элемент соответствует `nested_type`.

Пример:

```python
from restalchemy.dm import types


tags_type = types.TypedList(types.String(max_length=32))
```

### `Dict` и структурированные dict

- `Dict` проверяет, что значение — `dict` со строковыми ключами.
- `TypedDict(nested_type)` требует, чтобы все значения соответствовали `nested_type`.

Dict на основе схемы:

- `SoftSchemeDict(scheme)` — ключи должны быть подмножеством схемы.
- `SchemeDict(scheme)` — множество ключей должно строго совпадать со схемой.

Пример:

```python
from restalchemy.dm import types


settings_scheme = {
    "retries": types.Integer(min_value=0),
    "timeout": types.Float(min_value=0.0),
}

settings_type = types.SoftSchemeDict(settings_scheme)

settings = properties.property(settings_type, default=dict)
```

---

## Nullable и обёртки

### `AllowNone(nested_type)`

- Разрешает либо `None`, либо значение, валидное для `nested_type`.
- `to_simple_type()` / `from_simple_type()` делегируют в `nested_type`, если значение не `None`.
- `to_openapi_spec()` добавляет `nullable: true`.

Пример:

```python
maybe_uuid = types.AllowNone(types.UUID())

uuid_or_none = properties.property(maybe_uuid)
```

---

## Регулярные выражения и URL-типы

### `BaseRegExpType` и `BaseCompiledRegExpTypeFromAttr`

Базовые классы для типов, валидирующих строки по регулярному выражению.

Конкретные типы:

- `Uri` — URI-путь, заканчивающийся на UUID.
- `Mac` — MAC-адрес.
- `Hostname` (устаревший) — см. `types_network`.
- `Url` — HTTP/FTP URL.

---

## Динамические и сетевые типы

Дополнительные специализированные типы находятся в:

- `restalchemy.dm.types_dynamic`
- `restalchemy.dm.types_network`

Там можно найти:

- Более сложные типы для хостнеймов, сетей, подсетей.
- Динамические структуры со схемой, определяемой в рантайме.

Общий шаблон использования всегда один:

1. Создать экземпляр типа.
2. Использовать его в `properties.property()`.
3. Полагаться на DM-валидацию и конвертацию.

---

## Рекомендации

- Используйте DM-типы (`types.String`, `types.Integer` и др.), а не "сырой" Python-тип.
- Применяйте `AllowNone`, если поле действительно допускает `None`.
- Используйте `Enum` для небольших фиксированных наборов значений.
- Для сложных JSON-подобных структур предпочитайте `SoftSchemeDict`, `SchemeDict` или `TypedDict`, а не голый `Dict`.
