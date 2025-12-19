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

# 迁移概念（Migrations concepts）

RESTAlchemy 使用显式迁移文件来演进数据库模式。

迁移文件通常位于某个目录（例如 `examples/migrations/`），并通过 CLI 工具执行：`ra-new-migration`、`ra-apply-migration`、`ra-rollback-migration`、`ra-rename-migrations`。

---

## 迁移文件

每个迁移是一个包含 `migration_step` 对象的 Python 文件：

```python
from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["<prev-migration-file>.py"]

    @property
    def migration_id(self):
        return "<uuid>"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        pass

    def downgrade(self, session):
        pass


migration_step = MigrationStep()
```

模版文件位于：

- `restalchemy/storage/sql/migration_templ.tmpl`

CLI `ra-new-migration` 会基于该模板生成新迁移。

---

## 迁移标识与依赖

每个迁移包含：

- **UUID**（`migration_id`）。
- **依赖列表**（`self._depends`），即其它迁移文件名。
- **是否为手动迁移**（`is_manual`）。

依赖关系构成有向无环图（DAG）。应用某个迁移时，会先应用其所有依赖。

特殊常量：

- `HEAD` —— 表示“最新的自动迁移”。
- `MANUAL` —— 用于手动迁移文件名中的标记。

`MigrationEngine` 使用这些信息：

- 将部分名称解析为具体文件名。
- 计算“头部迁移”（head migration）。
- 检查自动迁移是否错误地依赖于手动迁移。

---

## 迁移文件名与编号

新迁移采用 **新的命名方案**：

```text
<migration_number>-<message-with-dashes>-<hash>.py
```

- `migration_number`：带前导零的编号（如 `0001`、`0002`）。
- `message-with-dashes`：由 `--message` 转换而来（空格替换为 `-`）。
- `hash`：迁移 UUID 的前 6 个字符。

手动迁移：

```text
MANUAL-<message-with-dashes>-<hash>.py
```

旧的命名方案仍然受支持，可以通过 `ra-rename-migrations` 将其统一转换为新方案并更新依赖字段。

如果 `--message` 以 4 位数字开头（长度等于默认编号长度），则该数字会直接用作 `migration_number`。

---

## 迁移状态跟踪

迁移应用状态记录在表 `ra_migrations` 中：

- 模型：`MigrationModel`。
- 字段：
  - `uuid`：主键，迁移 UUID。
  - `applied`：布尔值，表示迁移是否已应用。

`MigrationEngine` 会确保该表存在，并使用它：

- 找出尚未应用的迁移。
- 决定哪些迁移可以被回滚。

---

## 自动迁移与手动迁移

- **自动迁移**（`is_manual == False`）：
  - 只能依赖于其它自动迁移。
  - 用于计算 HEAD 迁移。
- **手动迁移**（`is_manual == True`）：
  - 通常包含复杂或不可逆的变更。
  - 不参与 HEAD 迁移的查找。

`ra-new-migration` 会检查：当 `--manual` 关闭时，自动迁移的依赖中不能出现手动迁移，否则命令会报错并退出。

---

## 典型工作流程

1. 定义并修改 DM 模型。
2. 当数据库结构发生变化时，使用 `ra-new-migration` 创建新的迁移文件。
3. 在迁移文件中实现 `upgrade()` / `downgrade()`。
4. 使用 `ra-apply-migration` 将迁移应用到目标数据库。
5. 如有需要，使用 `ra-rollback-migration` 回滚部分迁移。
6. 如需统一旧文件名，使用 `ra-rename-migrations` 进行重命名与依赖更新。
