#    Copyright 2026 Genesis Corporation.
#
#    All Rights Reserved.
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

import contextlib
import io
import unittest

from oslo_config import cfg

from restalchemy.common import config_opts


class TestPostgresqlConfigOpts(unittest.TestCase):
    def test_help_renders_literal_percent(self):
        conf = cfg.ConfigOpts()
        config_opts.register_postgresql_db_opts(conf)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as exc:
                conf(["--help"])

        self.assertEqual(0, exc.exception.code)
        self.assertIn("random 10% to avoid mass eviction", stdout.getvalue())
