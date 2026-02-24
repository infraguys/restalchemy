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

# Installation

This section explains how to install RESTAlchemy and its typical dependencies.

---

## Requirements

- A supported version of CPython (see RESTAlchemy on PyPI for exact versions).
- A virtual environment is strongly recommended.
- For SQL storage examples:
  - A running database (e.g. MySQL or PostgreSQL).
  - Matching Python drivers (e.g. `mysql-connector-python`, `psycopg`).

---

## Install RESTAlchemy

Create and activate a virtual environment (optional but recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the library from PyPI:

```bash
pip install restalchemy
```

To work with all examples in this repository, also install extra dependencies from `requirements.txt` (in the repository root):

```bash
pip install -r requirements.txt
```

---

## Verifying the installation

Run Python and import RESTAlchemy:

```python
import restalchemy
from restalchemy import version

print(version.__version__)
```

If this prints a version string without errors, the core installation works.

---

## Optional: database drivers

If you plan to use SQL storage:

- **MySQL**:
  - Install a MySQL driver, for example:
    ```bash
    pip install mysql-connector-python
    ```
- **PostgreSQL**:
  - Install a PostgreSQL driver, for example:
    ```bash
    pip install psycopg[binary]
    ```

Make sure the connection URLs you use in your code match the drivers and database you have installed.
