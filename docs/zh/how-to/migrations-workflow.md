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

为迁移选择一个目录，例如：

```text
myservice/
  migrations/
    ... migration files ...
```

本仓库的示例使用：

- `examples/migrations/`

所有 `ra-*` 命令都通过 `--path` / `-p` 指定迁移目录。

---

## 2. 创建新迁移

使用 `ra-new-migration` 命令：

```bash
ra-new-migration \
  --path examples/migrations/ \
  --message "create users table" \
  --depend HEAD
```

参数：

- `--path` / `-p`：迁移目录路径（必填）。
- `--message` / `-m`：简短描述；空格会被替换为 `-`。
- `--depend` / `-d`：零个或多个依赖（文件名或 `HEAD`）。
- `--manual`：标记为手动迁移。
- `--dry-run`：仅打印将要创建的内容，不写入文件。

典型场景：

- **依赖 HEAD 的自动迁移**：
  - `--depend HEAD`
  - 适合线性的迁移链。
- **手动迁移**：
  - `--manual`
  - 适用于与环境相关、或无法自动回滚的变更。

执行后会生成类似：

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

的文件，其中包含一个 `MigrationStep` 类，`upgrade()` 与 `downgrade()` 方法为空。你需要用实际的 SQL（或 DM/存储层）变更填充它们，并使用传入的 `session` 对象。

---

## 3. 实现 upgrade/downgrade

在生成的文件中实现迁移逻辑。

示例：

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

说明：

- `session.execute(statement, values)` 执行原生 SQL。
- `AbstractMigrationStep` 提供的辅助方法：
  - `_delete_table_if_exists(session, table_name)`
  - `_delete_trigger_if_exists(session, trigger_name)`
  - `_delete_view_if_exists(session, view_name)`

必要时也可以把原生 SQL 与更高层的存储/DM 逻辑结合使用。

---

## 4. 应用迁移

使用 `ra-apply-migration` 升级数据库：

```bash
ra-apply-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test
```

参数：

- `--path` / `-p`：迁移目录（必填）。
- `--db-connection`：数据库连接 URL（注册为 `db.connection_url`）。
- `--migration` / `-m`：目标迁移的名称或短名称；默认为 `HEAD`。
- `--dry-run`：演练执行，不做实际变更。

不指定 `-m` 时，命令会：

- 计算自动迁移的 HEAD。
- 应用直到该 HEAD 为止所有尚未应用的自动迁移。

指定 `-m X` 时：

- 应用为到达迁移 `X` 所需的、尚未应用的全部迁移。

若某个迁移已经应用过，则跳过并给出警告。

---

## 5. 回滚迁移

使用 `ra-rollback-migration` 把数据库回滚到指定迁移：

```bash
ra-rollback-migration \
  --path examples/migrations/ \
  --db-connection mysql://user:password@127.0.0.1/test \
  --migration 0003-add-index
```

参数：

- `--path` / `-p`：迁移目录（必填）。
- `--db-connection`：数据库连接 URL。
- `--migration` / `-m`：目标迁移名称（必填）。
- `--dry-run`：演练执行，不做实际变更。

回滚流程：

- 先按依赖的逆序回滚所有依赖目标迁移的迁移。
- 然后对目标迁移本身执行 `downgrade()`，并把它标记为未应用。

若某个迁移本来就未应用，则跳过并给出警告。

---

## 6. 将迁移改名为新的命名方案

使用 `ra-rename-migrations` 把已有的迁移文件名转换为新方案：

```bash
ra-rename-migrations --path examples/migrations/
```

工具会：

- 分析全部迁移文件，并为每个迁移计算索引。
- 给出新的文件名，形式为：

  - 自动迁移：`0001-oldname-<hash>.py`
  - 手动迁移：`MANUAL-oldname-<hash>.py`

- 在磁盘上重命名文件。
- 更新迁移文件内部的依赖引用，使其指向新文件名。

当你要从旧的短名称迁移到新的 `<编号>-<描述>-<hash>.py` 格式时，这一步很有用。

---

## 7. 推荐实践

- 将迁移文件纳入版本控制。
- `--message` 要简明准确，它会成为文件名的一部分。
- 常规结构变更优先使用自动迁移，手动迁移只留给确实特殊的场景。
- 在应用到生产环境之前，务必先在 CI 中针对测试数据库跑一遍迁移。
