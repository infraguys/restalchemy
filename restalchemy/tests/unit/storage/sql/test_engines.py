# Copyright 2019 Eugene Frolov
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

import mock
from oslo_config import cfg

from restalchemy.common import config_opts
from restalchemy.storage.sql import engines
from restalchemy.tests.unit import base


class TestEngineTestCase(base.BaseTestCase):
    @mock.patch("mysql.connector.pooling.MySQLConnectionPool")
    def setUp(self, *args):
        super(TestEngineTestCase, self).setUp()
        self._engine = engines.MySQLEngine(db_url="mysql://test:test@test/test")

    def tearDown(self):
        super(TestEngineTestCase, self).tearDown()
        del self._engine

    def test_session_manager_session_as_argument(self):
        session = mock.Mock()

        with self._engine.session_manager(session=session) as s:
            self.assertEqual(s, session)

    def test_session_manager_session_as_thread_storage(self):
        session = mock.Mock()

        with mock.patch.object(
            self._engine, "_get_session_from_storage", return_value=session
        ):
            with self._engine.session_manager() as s:
                self.assertEqual(s, session)

    def test_session_manager_get_new_session(self):
        session = mock.Mock()

        with mock.patch.object(self._engine, "get_session", return_value=session):
            with self._engine.session_manager() as s:
                self.assertEqual(s, session)


class DBConnectionUrlTestCase(base.BaseTestCase):
    """Test case for DBConnectionUrl instance"""

    _DB_URL_TEMPLATE = "mysql://john%s10.0.0.1/mydb"
    _DB_URL_CENSORED = _DB_URL_TEMPLATE % engines.DBConnectionUrl._CENSORED

    def test_repr_with_password(self):
        db_url = engines.DBConnectionUrl(self._DB_URL_TEMPLATE % ":my_cool_secret@")

        actual_repr = repr(db_url)
        actual_str = str(db_url)

        self.assertEqual(actual_repr, self._DB_URL_CENSORED)
        self.assertEqual(actual_str, actual_repr)

    def test_repr_with_empty_password(self):
        db_url = engines.DBConnectionUrl(self._DB_URL_TEMPLATE % ":@")

        actual_repr = repr(db_url)
        actual_str = str(db_url)

        self.assertEqual(actual_repr, self._DB_URL_CENSORED)
        self.assertEqual(actual_str, actual_repr)

    def test_repr_without_password(self):
        db_url = engines.DBConnectionUrl(self._DB_URL_TEMPLATE % "@")

        actual_repr = repr(db_url)
        actual_str = str(db_url)

        self.assertEqual(actual_repr, self._DB_URL_CENSORED)
        self.assertEqual(actual_str, actual_repr)


class PostgreSQLFactoryConfigTestCase(base.BaseTestCase):
    def setUp(self):
        super(PostgreSQLFactoryConfigTestCase, self).setUp()
        self.conf = cfg.ConfigOpts()
        config_opts.register_postgresql_db_opts(self.conf)
        self.conf([])

    def _configure(self):
        with mock.patch.object(
            engines.engine_factory, "configure_factory"
        ) as configure_factory:
            engines.engine_factory.configure_postgresql_factory(self.conf)
        return configure_factory.call_args.kwargs["config"]

    def test_connection_kwargs_are_omitted_by_default(self):
        config = self._configure()

        self.assertNotIn("kwargs", config)

    def test_explicit_zero_connection_timeouts_are_passed_to_psycopg(self):
        timeout_options = (
            "connection_connect_timeout",
            "connection_statement_timeout",
            "connection_transaction_timeout",
            "connection_idle_in_transaction_session_timeout",
            "connection_tcp_user_timeout",
            "connection_keepalives_idle",
            "connection_keepalives_interval",
            "connection_keepalives_count",
        )
        for option in timeout_options:
            self.conf.set_override(option, 0, group="db")

        config = self._configure()

        self.assertEqual(
            {
                "connect_timeout": 0,
                "keepalives_idle": 0,
                "keepalives_interval": 0,
                "keepalives_count": 0,
                "tcp_user_timeout": 0,
                "options": (
                    "-c statement_timeout=0"
                    " -c transaction_timeout=0"
                    " -c idle_in_transaction_session_timeout=0"
                ),
            },
            config["kwargs"],
        )

    def test_connection_timeouts_are_passed_to_psycopg(self):
        self.conf.set_override("connection_connect_timeout", 30, group="db")
        self.conf.set_override("connection_statement_timeout", 240, group="db")
        self.conf.set_override("connection_transaction_timeout", 300, group="db")
        self.conf.set_override(
            "connection_idle_in_transaction_session_timeout", 240, group="db"
        )
        self.conf.set_override("connection_tcp_user_timeout", 300, group="db")
        self.conf.set_override("connection_keepalives_idle", 60, group="db")
        self.conf.set_override("connection_keepalives_interval", 30, group="db")
        self.conf.set_override("connection_keepalives_count", 5, group="db")

        config = self._configure()

        self.assertEqual(
            {
                "connect_timeout": 30,
                "keepalives_idle": 60,
                "keepalives_interval": 30,
                "keepalives_count": 5,
                "tcp_user_timeout": 300000,
                "options": (
                    "-c statement_timeout=240000"
                    " -c transaction_timeout=300000"
                    " -c idle_in_transaction_session_timeout=240000"
                ),
            },
            config["kwargs"],
        )

    def test_connection_timeouts_preserve_url_options(self):
        self.conf.set_override(
            "connection_url",
            "postgresql://user:password@localhost/db"
            "?options=-c%20search_path%3Dapplication",
            group="db",
        )
        self.conf.set_override("connection_statement_timeout", 240, group="db")

        config = self._configure()

        self.assertEqual(
            "-c search_path=application -c statement_timeout=240000",
            config["kwargs"]["options"],
        )
