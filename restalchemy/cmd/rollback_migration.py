# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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
from restalchemy.common import log as ra_log
from restalchemy.storage.sql import engines
from restalchemy.storage.sql import migrations


cmd_opts = [
    cfg.StrOpt("migration", short="m", required=True,
               help="migrate to"),
    cfg.StrOpt('path', required=True, short="p",
               help="Path to migrations folder"),
    cfg.BoolOpt('dry-run', default=False,
                help="Dry run downgrade migration w/o any real changes.")
]

cmd_db_opts = [
    cfg.StrOpt("connection", required=True,
               help="connection string to database"),
]

CONF = cfg.CONF
CONF.register_cli_opts(cmd_opts)
CONF.register_cli_opts(cmd_db_opts, 'db')


def main():
    config.parse(sys.argv[1:])
    ra_log.configure()
    engines.engine_factory.configure_factory(db_url=CONF.db.connection)
    engine = migrations.MigrationEngine(migrations_path=CONF.path)
    engine.rollback_migration(migration_name=CONF.migration,
                              dry_run=CONF.dry_run)
