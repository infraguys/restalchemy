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

# DM + SQL storage how-to

В этом руководстве показано, как сохранять DM-модели в SQL-базу данных с помощью RESTAlchemy.

Вы научитесь:

- Определять DM-модели с `ModelWithUUID` и `SQLStorableMixin`.
- Настраивать SQL-движок (MySQL или PostgreSQL).
- Выполнять операции CRUD с помощью `.save()`, `.delete()` и `Model.objects`.
- Использовать фильтры для построения запросов.

Примеры основаны на `examples/dm_mysql_storage.py` и `examples/dm_pg_storage.py`.

---

## Предварительные условия

- RESTAlchemy установлен (см. `installation.md`).
- Запущенная база данных:
  - MySQL/MariaDB или
  - PostgreSQL.
- Установлен соответствующий Python-драйвер, например:
  - `mysql-connector-python` для MySQL.
  - `psycopg[binary]` для PostgreSQL.
- Таблицы созданы согласно описанию моделей (см. раздел про миграции ниже).

---

## 1. Определяем DM-модели для SQL

Минимальный паттерн для модели, работающей с SQL:

- Наследуемся от `models.ModelWithUUID` (или другого `ModelWithID`).
- Наследуемся от `orm.SQLStorableMixin`.
- Задаём `__tablename__` — имя таблицы.
- Описываем свойства DM и их типы.

Пример (упрощённый `dm_mysql_storage.py`):

```python
from restalchemy.dm import models, properties, relationships, types
from restalchemy.storage.sql import orm


class FooModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "foos"
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "bars"
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

Эти модели используют DM-валидацию и связи, а `SQLStorableMixin` добавляет методы для сохранения.

---

## 2. Настройка SQL-движка

Используйте `restalchemy.storage.sql.engines.engine_factory` для создания экземпляра движка.

### Пример для MySQL

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="mysql://user:password@127.0.0.1:3306/test",
)
```

### Пример для PostgreSQL

```python
from restalchemy.storage.sql import engines

engines.engine_factory.configure_factory(
    db_url="postgresql://postgres:password@127.0.0.1:5432/ra_tests",
)
```

`configure_factory()` нужно вызвать один раз при старте приложения. Затем все модели с `SQLStorableMixin` будут получать движок через `engine_factory.get_engine()`.

Дополнительные параметры:

- `config` — конфигурация движка (размеры пула, таймауты и т.п.).
- `query_cache` — включение кэша запросов на уровне сессии.

---

## 3. Создание таблиц и миграции

RESTAlchemy не создаёт таблицы автоматически; вместо этого используются миграции.

Команды миграций описаны в `README.rst`:

- `ra-new-migration` — создание новых файлов миграций.
- `ra-apply-migration` — применение миграций к целевой БД.

В примерах приведены наброски DDL, например в `dm_mysql_storage.py`:

```sql
CREATE TABLE `foos` (
     `uuid` CHAR(36) NOT NULL,
     `foo_field1` INT NOT NULL,
     `foo_field2` VARCHAR(255) NOT NULL,
 PRIMARY KEY (`uuid`)
) ENGINE = InnoDB;

CREATE TABLE `bars` (
    `uuid` CHAR(36) NOT NULL,
    `bar_field1` VARCHAR(10) NOT NULL,
    `foo` CHAR(36) NOT NULL,
    CONSTRAINT `_idx_foo` FOREIGN KEY (`foo`) REFERENCES `foos`(`uuid`)
) ENGINE = InnoDB;
```

Вы можете адаптировать эти схемы под свою БД или настроить миграции так, чтобы генерировать аналогичный DDL.

---

## 4. Базовые операции CRUD

После настройки движка и создания таблиц DM-модели можно использовать как постоянные сущности.

### Создание и сохранение

```python
foo1 = FooModel(foo_field1=10)
foo1.save()  # INSERT в foos

bar1 = BarModel(bar_field1="test", foo=foo1)
bar1.save()  # INSERT в bars
```

### Чтение данных

```python
# Все bars
all_bars = list(BarModel.objects.get_all())

# Один bar по первичному ключу
same_bar = BarModel.objects.get_one(filters={"uuid": bar1.get_id()})

# Все bars для конкретного FooModel
bars_for_foo = list(BarModel.objects.get_all(filters={"foo": foo1}))

# Преобразование в простой dict
print(bar1.as_plain_dict())
```

### Обновление

```python
foo2 = FooModel(foo_field1=11, foo_field2="some text")
foo2.save()

# Изменяем поле и сохраняем снова (UPDATE)
foo2.foo_field2 = "updated text"
foo2.save()
```

Если модель уже сохранена, `save()` вызывает `update()`, иначе — `insert()`.

### Удаление

```python
for foo in FooModel.objects.get_all():
    foo.delete()
```

Выполняется `DELETE` по ID-свойствам модели.

---

## 5. Фильтры

Фильтры определены в `restalchemy.dm.filters` и могут передаваться в `get_all()` и `get_one()`.

### Простые фильтры

```python
from restalchemy.dm import filters

# foo_field1 == 10
one = FooModel.objects.get_one(filters={"foo_field1": filters.EQ(10)})

# foo_field1 > 5
greater = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.GT(5)})
)

# foo_field1 IN (5, 6)
subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.In([5, 6])})
)

# foo_field1 NOT IN (1, 2)
not_subset = list(
    FooModel.objects.get_all(filters={"foo_field1": filters.NotIn([1, 2])})
)
```

### Сложные выражения

Можно строить сложные условия через `AND` и `OR`:

```python
from restalchemy.dm import filters

# WHERE ((foo_field1 = 1 AND foo_field2 = '2') OR (foo_field2 = '3'))
filter_expr = filters.OR(
    filters.AND(
        {
            "foo_field1": filters.EQ(1),
            "foo_field2": filters.EQ("2"),
        }
    ),
    filters.AND({"foo_field2": filters.EQ("3")}),
)

foo = FooModel.objects.get_one(filters=filter_expr)
```

Слой хранения переводит такие структуры в SQL WHERE-условия.

---

## 6. Транзакции и явные сессии

По умолчанию каждая операция использует собственную сессию и транзакцию.

Если нужно сгруппировать несколько операций в одну транзакцию, используйте `engine.session_manager()`.

### Пример с engine.session_manager()

```python
from restalchemy.storage.sql import engines

engine = engines.engine_factory.get_engine()

with engine.session_manager() as session:
    foo = FooModel(foo_field1=42)
    foo.save(session=session)

    bar = BarModel(bar_field1="x", foo=foo)
    bar.save(session=session)
    # В случае ошибки обе INSERT-операции будут откатаны.
```

Внутри блока `with` все операции разделяют одну и ту же сессию и транзакцию.

Также можно передавать уже созданную сессию в `.save()`, `.delete()` и методы коллекций через параметр `session=`.

---

## Резюме

- Описывайте DM-модели с `ModelWithUUID` + `SQLStorableMixin` и `__tablename__`.
- Настраивайте SQL-движок через `engine_factory.configure_factory()`.
- Используйте миграции для создания и изменения таблиц.
- Применяйте `.save()`, `.delete()` и `Model.objects.get_all()/get_one()` для CRUD.
- Используйте DM-фильтры для описания условий выборки.
- При необходимости контролируйте транзакции через явные сессии.
