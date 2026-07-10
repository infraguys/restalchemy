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

# SQL 引擎（SQL engines）

模块：`restalchemy.storage.sql.engines`

本模块包含引擎工厂以及 MySQL 和 PostgreSQL 的具体实现。

---

## AbstractEngine

`AbstractEngine` 定义了所有 SQL 引擎的通用行为：

- 解析数据库 URL。
- 暴露 `db_name`、`db_host`、`db_port`、`db_username`、`db_password`。
- 持有 SQL 方言对象。
- 提供 `session_manager()` 上下文管理器。

---

## PgSQLEngine

- `URL_SCHEMA = "postgresql"`。
- 使用 `psycopg_pool.ConnectionPool`。
- 方言：`pgsql.PgSQLDialect()`。
- 会话类：`sessions.PgSQLSession`。

### 连接超时

`register_postgresql_db_opts()` 注册连接、服务器和 TCP 超时设置。时长以秒为
单位；`0` 表示保留 libpq、PostgreSQL 或操作系统的相应默认值。

- `connection_connect_timeout`：建立连接的最长时间。
- `connection_statement_timeout`：单条语句的最长执行时间。
- `connection_transaction_timeout`：事务的最长持续时间；需要 PostgreSQL 17
  或更高版本。
- `connection_idle_in_transaction_session_timeout`：会话在事务中保持空闲的
  最长时间。
- `connection_tcp_user_timeout`：已发送数据未被确认的最长时间。
- `connection_keepalives_idle`、`connection_keepalives_interval` 和
  `connection_keepalives_count`：TCP keepalive 检测参数。

示例：

```ini
[db]
connection_connect_timeout = 30
connection_statement_timeout = 240
connection_transaction_timeout = 300
connection_idle_in_transaction_session_timeout = 240
connection_tcp_user_timeout = 300
connection_keepalives_idle = 60
connection_keepalives_interval = 30
connection_keepalives_count = 5
```

---

## MySQLEngine

- `URL_SCHEMA = "mysql"`。
- 使用 `mysql.connector.pooling.MySQLConnectionPool`。
- 方言：`mysql.MySQLDialect()`。
- 会话类：`sessions.MySQLSession`。

---

## EngineFactory

- `configure_factory(db_url, config=None, query_cache=False, name="default")`：配置引擎。
- `get_engine(name="default")`：获取引擎实例。
- `destroy_engine()` / `destroy_all_engines()`：销毁引擎。

模块级单例：

```python
engine_factory = EngineFactory()
```
