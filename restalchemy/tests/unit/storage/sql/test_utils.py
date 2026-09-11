# Copyright 2025
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

from restalchemy.storage.sql import utils
from restalchemy.tests.unit import base


class SavepointCtxTestCase(base.BaseTestCase):
    def _make_ctx(self, dialect_name):
        engine = mock.Mock()
        engine.dialect.name = dialect_name

        ctx = mock.Mock()
        ctx._engine = engine
        ctx.get_session.return_value = mock.Mock()
        return ctx

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_postgresql_success(self, mock_ctx_cls):
        ctx = self._make_ctx("postgresql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with utils.savepoint("sp") as s:
            self.assertIs(s, session)

        session.execute.assert_any_call("SAVEPOINT sp;", tuple())
        session.execute.assert_any_call("RELEASE SAVEPOINT sp;", tuple())

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_postgresql_error(self, mock_ctx_cls):
        ctx = self._make_ctx("postgresql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with self.assertRaises(RuntimeError):
            with utils.savepoint("sp"):
                raise RuntimeError("boom")

        session.execute.assert_any_call("SAVEPOINT sp;", tuple())
        session.execute.assert_any_call("ROLLBACK TO SAVEPOINT sp;", tuple())
        session.execute.assert_any_call("RELEASE SAVEPOINT sp;", tuple())

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_mysql_success(self, mock_ctx_cls):
        ctx = self._make_ctx("mysql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with utils.savepoint("sp") as s:
            self.assertIs(s, session)

        session.execute.assert_any_call("SAVEPOINT sp;", tuple())
        session.execute.assert_any_call("RELEASE SAVEPOINT sp;", tuple())

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_mysql_error(self, mock_ctx_cls):
        ctx = self._make_ctx("mysql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with self.assertRaises(RuntimeError):
            with utils.savepoint("sp"):
                raise RuntimeError("boom")

        session.execute.assert_any_call("SAVEPOINT sp;", tuple())
        session.execute.assert_any_call("ROLLBACK TO sp;", tuple())
        session.execute.assert_any_call("RELEASE SAVEPOINT sp;", tuple())

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_defer_release_success_skips_release(self, mock_ctx_cls):
        ctx = self._make_ctx("postgresql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with utils.savepoint("sp", defer_release=True) as s:
            self.assertIs(s, session)

        executed = [call.args[0] for call in session.execute.call_args_list]
        self.assertEqual(executed, ["SAVEPOINT sp;"])

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_defer_release_error_still_releases(self, mock_ctx_cls):
        ctx = self._make_ctx("postgresql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with self.assertRaises(RuntimeError):
            with utils.savepoint("sp", defer_release=True):
                raise RuntimeError("boom")

        session.execute.assert_any_call("SAVEPOINT sp;", tuple())
        session.execute.assert_any_call("ROLLBACK TO SAVEPOINT sp;", tuple())
        session.execute.assert_any_call("RELEASE SAVEPOINT sp;", tuple())

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_keyboard_interrupt_releases_and_propagates(
        self, mock_ctx_cls
    ):
        ctx = self._make_ctx("postgresql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with self.assertRaises(KeyboardInterrupt):
            with utils.savepoint("sp"):
                raise KeyboardInterrupt()

        executed = [call.args[0] for call in session.execute.call_args_list]
        self.assertEqual(
            executed,
            ["SAVEPOINT sp;", "RELEASE SAVEPOINT sp;"],
        )

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_defer_release_keyboard_interrupt_releases_and_propagates(
        self, mock_ctx_cls
    ):
        ctx = self._make_ctx("postgresql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with self.assertRaises(KeyboardInterrupt):
            with utils.savepoint("sp", defer_release=True):
                raise KeyboardInterrupt()

        executed = [call.args[0] for call in session.execute.call_args_list]
        self.assertEqual(
            executed,
            ["SAVEPOINT sp;", "RELEASE SAVEPOINT sp;"],
        )

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_system_exit_releases_and_propagates(self, mock_ctx_cls):
        ctx = self._make_ctx("postgresql")
        mock_ctx_cls.return_value = ctx

        session = ctx.get_session.return_value

        with self.assertRaises(SystemExit):
            with utils.savepoint("sp", defer_release=True):
                raise SystemExit(1)

        executed = [call.args[0] for call in session.execute.call_args_list]
        self.assertEqual(
            executed,
            ["SAVEPOINT sp;", "RELEASE SAVEPOINT sp;"],
        )

    def test_savepoint_invalid_name_raises(self):
        with self.assertRaises(ValueError):
            with utils.savepoint("invalid name!"):
                pass

    @mock.patch("restalchemy.storage.sql.utils.contexts.Context")
    def test_savepoint_unsupported_dialect_raises(self, mock_ctx_cls):
        ctx = self._make_ctx("sqlite")
        mock_ctx_cls.return_value = ctx

        with self.assertRaises(ValueError):
            with utils.savepoint("sp"):
                pass
