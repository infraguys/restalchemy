# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

import sys

from oslo_config import cfg

from restalchemy.common import config
from restalchemy.common import config_opts
from restalchemy.common import log as ra_log
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import migrations

cmd_opts = [
    cfg.StrOpt(
        "migration",
        default=migrations.HEAD_MIGRATION,
        short="m",
        required=False,
        help="migrate to given migration."
        "If migration is not specified, HEAD migration will be used",
    ),
    cfg.StrOpt(
        "path",
        required=True,
        short="p",
        help="Path to migrations folder",
    ),
    cfg.BoolOpt(
        "dry-run",
        default=False,
        help="Dry run upgrade for migration w/o any real changes.",
    ),
]


CONF = cfg.CONF
CONF.register_cli_opts(cmd_opts)
config_opts.register_common_db_opts(conf=CONF)


def main():
    config.parse(sys.argv[1:])
    ra_log.configure()
    engines.engine_factory.configure_factory(db_url=CONF.db.connection_url)
    engine = migrations.MigrationEngine(migrations_path=CONF.path)

    migration = (
        engine.get_latest_migration()
        if CONF.migration.upper() == migrations.HEAD_MIGRATION
        else CONF.migration
    )
    engine.apply_migration(migration_name=migration, dry_run=CONF.dry_run)


if __name__ == "__main__":
    main()
