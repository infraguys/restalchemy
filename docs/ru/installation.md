# Установка

В этом разделе описывается установка RESTAlchemy и типичных зависимостей.

---

## Требования

- Поддерживаемая версия CPython (точные версии см. на странице RESTAlchemy в PyPI).
- Настоятельно рекомендуется использовать виртуальное окружение.
- Для примеров с SQL-хранилищем:
  - Запущенная база данных (например, MySQL или PostgreSQL).
  - Соответствующие Python-драйверы (например, `mysql-connector-python`, `psycopg`).

---

## Установка RESTAlchemy

Создайте и активируйте виртуальное окружение (рекомендуется):

```bash
python -m venv .venv
source .venv/bin/activate
```

Установите библиотеку из PyPI:

```bash
pip install restalchemy
```

Чтобы запустить все примеры из репозитория, дополнительно установите зависимости из `requirements.txt` (в корне репозитория):

```bash
pip install -r requirements.txt
```

---

## Проверка установки

Запустите Python и выполните:

```python
import restalchemy
from restalchemy import version

print(version.__version__)
```

Если версия выводится без ошибок, базовая установка выполнена корректно.

---

## Дополнительно: драйверы баз данных

Если вы планируете использовать SQL-хранилище:

- **MySQL**:
  - Установите драйвер MySQL, например:
    ```bash
    pip install mysql-connector-python
    ```
- **PostgreSQL**:
  - Установите драйвер PostgreSQL, например:
    ```bash
    pip install psycopg[binary]
    ```

Убедитесь, что строки подключения в коде соответствуют установленным драйверам и используемой СУБД.
