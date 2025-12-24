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

# Нюансы сериализации результатов actions

Этот документ описывает важный нюанс RESTAlchemy: **как именно выбирается сериализатор (packer) и набор полей ресурса при обработке `actions`**, и почему action, объявленный на контроллере ресурса `A`, по умолчанию сериализуется *как ресурс `A`*, даже если фактически возвращает модель `B`.

Также приводится практический паттерн обхода (без правок библиотеки) и ссылки на рабочий пример в функциональных тестах.

---

## TL;DR

- Action выполняется **в контексте контроллера**, на котором он объявлен/к которому привязан.
- **Packer и схема сериализации берутся из `__resource__` этого контроллера.**
- Если action вернул модель другого типа, packer начнёт читать «чужие» поля и упадёт с `AttributeError`.
- Практичный обход без модификации RestAlchemy: **привязывать action к отдельному контроллеру**, у которого `__resource__` соответствует типу возвращаемых моделей.

---

## 1. Почему так происходит

### 1.1. Общий поток обработки action

Упрощённо, для URL вида:

- `/v1/vms/<uuid>/actions/ip_addresses`

происходит:

1. Router резолвит route дерева (например, `v1 → vms → actions/ip_addresses`).
2. По `<uuid>` загружается родительский ресурс VM (это **вход** в action).
3. Выбирается класс action (`routes.Action`) и его `__controller__`.
4. Вызывается метод контроллера, помеченный `@actions.get`/`@actions.post`.
5. Результат передаётся в `controller.process_result()`.
6. `process_result()` строит HTTP response через `controller.get_packer()`.
7. `packer` сериализует объект, используя **поля ресурса из `controller.__resource__`**.

### 1.2. Ключевой нюанс

`packer` не «угадывает» тип модели по возвращаемому значению (и не использует OpenAPI-аннотации для runtime). Он сериализует ответ **как тот ресурс, к которому привязан контроллер**.

Если контроллер объявлен как:

- `__resource__ = ResourceByRAModel(models.VM)`

то packer ожидает, что объекты ответа содержат поля VM (например, `state`, `name`, …).

---

## 2. Симптомы проблемы

### 2.1. Типичный стек ошибки

Если action на контроллере VM вернёт `IpAddress`, то packer, сериализующий «как VM», попытается прочитать у `IpAddress` поле `state`:

- `AttributeError: IpAddress object has no attribute state`

Это выглядит как «сломанная сериализация моделей в actions», но по сути это **неконсистентность между типом `__resource__` контроллера и типом фактического результата action**.

---

## 3. Практический пример из функциональных тестов (VM → IpAddress)

### 3.1. Цель

Сделать endpoint action:

- `GET /v1/vms/<uuid>/actions/ip_addresses`

который возвращает **список `IpAddress`** для данной VM.

### 3.2. Почему нельзя просто вернуть `IpAddress` из `VMController`

Если разместить `ip_addresses()` прямо в `VMController`, то сериализация будет выполняться как `VM` и упадёт (см. раздел 2).

### 3.3. Решение без правок библиотеки (вариант 1)

Решение состоит из двух частей:

- **(A) Отдельный контроллер для action результата** с правильным `__resource__`.
- **(B) Привязать `routes.Action` к этому контроллеру**.

#### A) Контроллер результата

Файл:

- `restalchemy/tests/functional/restapi/ra_based/microservice/controllers.py`

Класс:

- `VMIpAddressesController`

Идея: входным параметром `resource` остаётся VM (родительский ресурс), но **`__resource__` выставлен как IpAddress**, поэтому packer сериализует результат корректно.

Дополнительный нюанс: в RestAlchemy есть глобальная таблица соответствия `model → resource`.

- Если создать второй `ResourceByRAModel(models.IpAddress)`, будет ошибка о duplicate mapping.
- Поэтому ресурс **переиспользуется**: `IpAddressController.__resource__`.

#### B) Route action

Файл:

- `restalchemy/tests/functional/restapi/ra_based/microservice/routes.py`

Класс:

- `VMIPAddressesAction`

Он должен указывать на `VMIpAddressesController`, а в `VMRoute` action объявляется как:

- `ip_addresses = routes.action(VMIPAddressesAction, invoke=False)`

### 3.4. Тест, фиксирующий корректное поведение

Файл:

- `restalchemy/tests/functional/restapi/ra_based/test_resources.py`

Тест:

- `TestRetryOnErrorMiddlewareBaseResourceTestCase.test_vm_get_ip_addresses_action_returns_success`

Проверяет:

- HTTP 200
- JSON-ответ — список объектов IpAddress вида:
  - `uuid`
  - `ip`
  - `port` (URI на порт)

---

## 4. Рекомендации

### 4.1. Когда использовать отдельный контроллер (рекомендуется)

Используйте отдельный контроллер, если:

- action возвращает **модель другого типа** (или список таких моделей),
- вы хотите сохранить action endpoint (а не добавлять отдельный nested route),
- вы не хотите модифицировать RestAlchemy.

Это даёт:

- правильный packer,
- правильный набор полей,
- воспроизводимость и предсказуемость.

### 4.2. Когда лучше вернуть `dict`/primitive

Если результат не является ресурсом/моделью (например, `{"state": "on"}`), лучше возвращать простые структуры (`dict`, `list[dict]`, строки), т.к. они сериализуются без привязки к полям `__resource__`.

### 4.3. Что делать, если нужно «универсально» в одном action

Если action потенциально может вернуть разные типы (то VM, то IpAddress) — это плохой контракт:

- packer не сможет корректно сериализовать оба типа в рамках одного `__resource__`.

В таком случае лучше:

- разнести на разные endpoints/controllers,
- либо менять библиотеку (см. отдельные дизайн-варианты: «action-specific resource type»).

---

## 5. См. также

- How-to по nested resources и actions:
  - `docs/ru/how-to/api-nested-resources-and-actions.md`
