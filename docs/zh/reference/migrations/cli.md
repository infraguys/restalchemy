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

# 迁移 CLI 参考（Migrations CLI reference）

本节介绍管理迁移的命令行工具：

- `ra-new-migration`
- `ra-apply-migration`
- `ra-rollback-migration`
- `ra-rename-migrations`

所有命令底层都使用 `oslo_config`，同时支持长选项与短选项。

---

## `ra-new-migration`

基于模板创建新的迁移文件。

### 用法

```bash
ra-new-migration \
  --path <path-to-migrations> \
  --message "1st migration" \
  --depend HEAD \
  [--manual] \
  [--dry-run]
```

### 参数

- `--path` / `-p`（必填）
  - 迁移目录路径。
- `--message` / `-m`
  - 可读的描述；文件名中的空格会被替换为 `-`。
- `--depend` / `-d`
  - 可多次指定。
  - 取值为下列之一：
    - 迁移文件名的子串；或
    - 特殊值 `HEAD`。
- `--manual`
  - 将迁移标记为手动迁移（`is_manual = True`）。
- `--dry-run`
  - 只打印将要创建的内容，不写入文件。

如果迁移不是手动迁移，工具会校验自动迁移不依赖手动迁移；否则以退出码 `1` 结束。

文件由 `migration_templ.tmpl` 生成，并填入：

- `migration_id`：UUID。
- `depends`：解析后的依赖文件名。
- `is_manual`：布尔值。

---

## `ra-apply-migration`

将迁移应用到指定的目标迁移。

### 用法

```bash
ra-apply-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  [--migration <name-or-HEAD>] \
  [--dry-run]
```

### 参数

- `--path` / `-p`（必填）
  - 迁移目录路径。
- `--db-connection`
  - 数据库连接 URL，通过 `config_opts.register_common_db_opts` 保存为 `CONF.db.connection_url`。
- `--migration` / `-m`
  - 目标迁移的名称或短名称。
  - 默认值：`HEAD`（最新的自动迁移）。
- `--dry-run`
  - 演练执行，不调用 `upgrade()`。

### 行为

- 通过 `engine_factory.configure_factory(db_url=CONF.db.connection_url)` 配置 SQL 引擎。
- 使用 `MigrationEngine(migrations_path=CONF.path)` 完成：
  - 必要时解析 `HEAD`。
  - 应用全部所需迁移（先处理依赖）。
  - 调用 `upgrade()` 并将迁移标记为已应用。

---

## `ra-rollback-migration`

将迁移回滚到指定的目标迁移。

### 用法

```bash
ra-rollback-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  --migration <name> \
  [--dry-run]
```

### 参数

- `--path` / `-p`（必填）
- `--db-connection`（必填）
- `--migration` / `-m`（必填）
  - 目标迁移名称。
- `--dry-run`
  - 演练执行，不调用 `downgrade()`。

### 行为

- 与 `ra-apply-migration` 类似地配置 SQL 引擎。
- 使用 `MigrationEngine.rollback_migration()`，它会：
  - 确保 `ra_migrations` 表存在。
  - 加载迁移控制器。
  - 先回滚依赖它的迁移，再回滚目标迁移。

---

## `ra-rename-migrations`

将迁移文件重命名为新的命名方案，并更新依赖。

### 用法

```bash
ra-rename-migrations --path <path-to-migrations>
```

### 参数

- `--path` / `-p`（必填）
  - 迁移目录路径。

### 行为

- 为给定路径构建 `MigrationEngine`。
- 调用 `engine.get_all_migrations()` 获取元数据：
  - `index`、`uuid`、`depends`、`is_manual`。
- 对每个文件：
  - 给出新的文件名：
    - 自动迁移：`<index>-<oldname>-<uuid_prefix>.py`。
    - 手动迁移：`MANUAL-<oldname>-<uuid_prefix>.py`。
  - 重命名该文件。
  - 如果该迁移存在依赖：
    - 打开新文件。
    - 将依赖字符串由旧文件名改写为建议的新文件名。

这是一次性的工具化步骤，用于把已有项目迁移到新的命名约定。
