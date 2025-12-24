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

# 安装

本节介绍如何安装 RESTAlchemy 以及常见依赖。

---

## 环境要求

- 支持的 CPython 版本（具体版本请参考 PyPI 上的 RESTAlchemy 页面）。
- 强烈建议使用虚拟环境。
- 如果要运行 SQL 存储示例：
  - 需要一套正在运行的数据库（例如 MySQL 或 PostgreSQL）。
  - 对应的 Python 驱动（如 `mysql-connector-python`、`psycopg`）。

---

## 安装 RESTAlchemy

（推荐）先创建并激活虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

从 PyPI 安装库：

```bash
pip install restalchemy
```

要运行仓库中的所有示例，可以安装根目录下 `requirements.txt` 中的依赖：

```bash
pip install -r requirements.txt
```

---

## 验证安装

启动 Python 并执行：

```python
import restalchemy
from restalchemy import version

print(version.__version__)
```

如果可以正常打印版本号，说明基础安装成功。

---

## 可选：数据库驱动

如果计划使用 SQL 存储：

- **MySQL**：
  - 安装 MySQL 驱动，例如：
    ```bash
    pip install mysql-connector-python
    ```
- **PostgreSQL**：
  - 安装 PostgreSQL 驱动，例如：
    ```bash
    pip install psycopg[binary]
    ```

请确保你在代码中使用的连接 URL 与已安装的驱动和所用数据库类型一致。
