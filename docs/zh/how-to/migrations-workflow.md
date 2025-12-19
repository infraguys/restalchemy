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

# 迁移工作流程（Migrations workflow）

本指南介绍在 RESTAlchemy 中管理 SQL 模式迁移的常见流程。

你将学习：

- 如何组织迁移目录。
- 如何使用 `ra-new-migration` 创建迁移。
- 如何使用 `ra-apply-migration` 应用迁移。
- 如何使用 `ra-rollback-migration` 回滚迁移。
- 如何使用 `ra-rename-migrations` 迁移旧文件名到新命名方案。

---

## 1. 目录结构

```text
myservice/
  migrations/
    ... migration files ...
```

示例仓库中使用：`examples/migrations/`。

所有 `ra-*` 命令都通过 `--path` / `-p` 指定迁移目录。

---

## 2. 创建新迁移

```bash
ra-new-migration \
  --path examples/migrations/ \
  --message "create users table" \
  --depend HEAD
```

关键参数：

- `--path` / `-p`：迁移目录路径（必填）。
- `--message` / `-m`：迁移描述，空格会被替换为 `-`。
- `--depend` / `-d`：依赖（文件名或 `HEAD`）。
- `--manual`：标记为手动迁移。
- `--dry-run`：仅打印，不真实写入文件。

执行后会生成类似：

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

的文件，并包含 `MigrationStep` 类与空的 `upgrade()`、`downgrade()` 方法。

---

## 3. 实现 upgrade/downgrade

在新文件中实现迁移逻辑：

```python
from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["0001-create-users-abcdef.py"]

    @property
    def migration_id(self):
        return "...uuid..."

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        session.execute(
            """CREATE TABLE users (
                   uuid CHAR(36) PRIMARY KEY,
                   name VARCHAR(255) NOT NULL
               )""",
            None,
        )

    def downgrade(self, session):
        self._delete_table_if_exists(session, "users")


migration_step = MigrationStep()
```

可使用 `AbstractMigrationStep` 的辅助方法删除表、触发器或视图。

---

## 4. 应用迁移

```bash
ra-apply-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test
```

主要参数：

- `--path` / `-p`：迁移目录。
- `--db-connection`：数据库连接 URL。
- `--migration` / `-m`：目标迁移，默认为 `HEAD`。
- `--dry-run`：仅输出计划，不实际执行。

不指定 `-m` 时，会自动查找 HEAD 迁移并应用到最新。

---

## 5. 回滚迁移

```bash
ra-rollback-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test \
  --migration 0003-add-index
```

- `--path` / `-p`：迁移目录。
- `--db-connection`：数据库连接 URL。
- `--migration` / `-m`：回滚到的目标迁移。
- `--dry-run`：仅打印，不执行。

流程：先回滚依赖于目标迁移的所有迁移，再回滚目标自身。

---

## 6. 迁移文件重命名

```bash
ra-rename-migrations --path examples/migrations/
```

工具会：

- 读取所有迁移、计算索引。
- 将文件名转换为新格式 `0001-oldname-<hash>.py` / `MANUAL-oldname-<hash>.py`。
- 更新迁移文件中的依赖引用。

---

## 7. 建议

- 将迁移目录纳入版本控制。
- `--message` 要简明准确，会进入文件名。
- 将常规结构变更放入自动迁移；仅在必要时使用手动迁移。
- 在 CI 和测试数据库上先跑一遍所有迁移，再应用到生产环境。
