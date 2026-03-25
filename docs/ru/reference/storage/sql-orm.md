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

# SQL ORM-mixin-ы и коллекции

Модуль: `restalchemy.storage.sql.orm`

Модуль предоставляет ORM-подобное поведение для DM-моделей:

- `ObjectCollection` — коллекция объектов, доступная как `Model.objects`.
- `SQLStorableMixin` — mixin, добавляющий `save()`, `update()`, `delete()` и интеграцию с SQL-таблицами.
- `SQLStorableWithJSONFieldsMixin` — специализация для моделей с JSON-полями.

---

## ObjectCollection

`ObjectCollection` реализует интерфейс коллекции для моделей, хранимых в SQL.

Ключевые методы:

- `get_all(filters=None, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - Возвращает список экземпляров модели.
  - Использует `filters` (структуры из `restalchemy.dm.filters`) для построения WHERE-условий.
  - При `cache=True` использует кэш запросов на уровне сессии.
- `get_one(filters=None, session=None, cache=False, locked=False)`
  - Возвращает ровно одну запись.
  - Бросает `RecordNotFound`, если записей нет, и `HasManyRecords`, если более одной.
- `get_one_or_none(filters=None, session=None, cache=False, locked=False)`
  - Возвращает одну запись или `None`, если ничего не найдено.
- `query(where_conditions, where_values, session=None, cache=False, limit=None, order_by=None, locked=False)`
  - Выполняет кастомный SELECT с произвольным WHERE.
- `count(session=None, filters=None)`
  - Возвращает количество записей, удовлетворяющих фильтру.

`ObjectCollection` использует:

- Диалект SQL через `engine.dialect`.
- Метод модели `restore_from_storage()` для конвертации строк из БД в DM-модели.

---

## SQLStorableMixin

`SQLStorableMixin` используется совместно с DM-моделями для их хранения в SQL.

### Требования

- Модель должна иметь строковый атрибут `__tablename__`.
- Должно быть хотя бы одно ID-свойство (`id_property=True`).

### Ответственность

- `get_table()`
  - Возвращает объект `SQLTable` для модели, кэшируемый в `__operational_storage__`.
- `insert(session=None)`
  - Выполняет INSERT на основе текущих значений свойств.
- `save(session=None)`
  - Вызывает `insert()` для новых объектов и `update()` для уже сохранённых.
- `update(session=None, force=False)`
  - Обновляет строку, если модель "грязная" (`is_dirty()`) или `force=True`.
  - Перед обновлением вызывает `validate()`.
  - Гарантирует, что обновлена ровно одна строка, иначе бросает исключение.
- `delete(session=None)`
  - Удаляет строку по ID-свойствам.
- `restore_from_storage(**kwargs)` (classmethod)
  - Преобразует значения из БД (простые типы) в значения DM-свойств.
  - Создаёт экземпляр модели, помеченный как "сохранённый".

### Привязка коллекции объектов

`SQLStorableMixin` определяет `_ObjectCollection = ObjectCollection`. В комбинации с базовыми классами storage это даёт:

- `Model.objects` — коллекцию, работающую через `ObjectCollection`.

### Помощники преобразований типов

- `to_simple_type(value)` (classmethod)
  - Конвертирует экземпляры модели или "сырые" ID в вид, пригодный для фильтров.
- `from_simple_type(value)` (classmethod)
  - Конвертирует ID или результат prefetch в экземпляр модели.

---

## SQLStorableWithJSONFieldsMixin

`SQLStorableWithJSONFieldsMixin` расширяет `SQLStorableMixin` для БД без нативной поддержки JSON-полей.

Паттерн использования:

- Наследуемся от `SQLStorableWithJSONFieldsMixin` вместо `SQLStorableMixin`.
- Определяем `__jsonfields__` как перечень имён полей с JSON-данными.

Поведение:

- `restore_from_storage()`
  - Для полей из `__jsonfields__`, если хранимое значение — строка, парсит его как JSON.
- `_get_prepared_data(properties=None)`
  - Для полей из `__jsonfields__` сериализует Python-структуры в компактные JSON-строки.

Это позволяет использовать JSON-поля в DM-модели и хранить их как текст в БД, не поддерживающей JSON нативно.
