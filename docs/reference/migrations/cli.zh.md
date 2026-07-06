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

---

## `ra-new-migration`

创建新的迁移文件。

```bash
ra-new-migration \
  --path <path-to-migrations> \
  --message "1st migration" \
  --depend HEAD \
  [--manual] \
  [--dry-run]
```

关键参数：

- `--path` / `-p`：迁移目录路径。
- `--message` / `-m`：描述字符串。
- `--depend` / `-d`：依赖，可多次指定，支持 `HEAD`。
- `--manual`：标记为手动迁移。
- `--dry-run`：仅打印不写入文件。

---

## `ra-apply-migration`

应用迁移（升级数据库）。

```bash
ra-apply-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  [--migration <name-or-HEAD>] \
  [--dry-run]
```

- `--path` / `-p`：迁移目录。
- `--db-connection`：数据库 URL。
- `--migration` / `-m`：目标迁移名称或 `HEAD`（默认）。
- `--dry-run`：仅演示不执行。

---

## `ra-rollback-migration`

回滚迁移（降级数据库）。

```bash
ra-rollback-migration \
  --path <path-to-migrations> \
  --db-connection <db-url> \
  --migration <name> \
  [--dry-run]
```

- `--path` / `-p`：迁移目录。
- `--db-connection`：数据库 URL。
- `--migration` / `-m`：目标迁移名称。
- `--dry-run`：仅演示不执行。

---

## `ra-rename-migrations`

将旧迁移文件重命名为新的命名方案，并更新依赖。

```bash
ra-rename-migrations --path <path-to-migrations>
```

- `--path` / `-p`：迁移目录。

工具会：

- 计算每个迁移对应的索引和值。
- 生成新文件名并重命名。
- 修改迁移文件中的依赖引用为新文件名。
