# Copyright 2023 George Melikov
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
import os
import sys

from oslo_config import cfg

from restalchemy.common import config
from restalchemy.common import log as ra_log
from restalchemy.storage.sql import migrations


def suggest_filename(file, migration_files):
    index = "{:04d}".format(migration_files["index"])
    filename = file.rstrip(".py")
    uuid = migration_files["uuid"].split("-")[0][:6]

    if not migration_files["is_manual"]:
        result = "{}-{}-{}.py".format(index, filename, uuid)
    else:
        result = "MANUAL-{}-{}.py".format(filename, uuid)

    return result


cmd_opts = [
    cfg.StrOpt(
        "path",
        required=True,
        short="p",
        help="Path to migrations folder",
    ),
]

CONF = cfg.CONF
CONF.register_cli_opts(cmd_opts)


def main():
    config.parse(sys.argv[1:])
    ra_log.configure()

    engine = migrations.MigrationEngine(migrations_path=CONF.path)

    migration_files = engine.get_all_migrations()

    logging.info("Parsing files in folder - %s", CONF.path)

    for file in migration_files.keys():
        suggested_name = suggest_filename(file, migration_files[file])

        logging.info("Renaming %s to %s", file, suggested_name)

        os.rename(
            os.path.join(CONF.path, file),
            os.path.join(CONF.path, suggested_name),
        )

        if not migration_files[file]["depends"]:
            continue

        with open(os.path.join(CONF.path, suggested_name), "r+") as f:
            content = f.read()

            for d in migration_files[file]["depends"]:
                suggested_depends_name = suggest_filename(
                    d,
                    migration_files[d],
                )
                logging.info(
                    "Renaming depends %s to %s",
                    d,
                    suggested_depends_name,
                )
                content = content.replace(d, suggested_depends_name)

            f.seek(0)

            f.write(content)

            f.truncate()


if __name__ == "__main__":
    main()
