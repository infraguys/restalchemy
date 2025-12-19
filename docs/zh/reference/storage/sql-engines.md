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
