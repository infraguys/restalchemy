#    Copyright 2019 George Melikov.
#
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
import unittest

from restalchemy.storage.sql import engines
from restalchemy.storage.sql import sessions

from restalchemy.common import contexts


class SomeError(Exception):
    pass


@mock.patch("restalchemy.storage.sql.engines.engine_factory")
class TestContext(unittest.TestCase):

    def _configure_mocks(self, engine_factory_mock):
        self._engine = mock.Mock(spec=engines.MySQLEngine)
        self._storage = mock.Mock(spec=sessions.SessionThreadStorage)
        self._session = mock.Mock(spec=sessions.MySQLSession)
        # Configure mocks
        engine_factory_mock.configure_mock(
            **{
                "get_engine.return_value": self._engine,
            }
        )
        self._engine.configure_mock(
            **{
                "get_session.return_value": self._session,
                "get_session_storage.return_value": self._storage,
            }
        )
        self._storage.configure_mock(
            **{
                "get_session.return_value": self._session,
            }
        )

    def test_context_manager_no_exceptions(self, engine_factory_mock):
        self._configure_mocks(engine_factory_mock)
        context = contexts.Context()

        with context.session_manager():
            pass

        self._session.commit.assert_called_once()
        self._session.close.assert_called_once()
        self._storage.remove_session.assert_called_once()

    def test_context_manager_service_error(self, engine_factory_mock):
        self._configure_mocks(engine_factory_mock)
        context = contexts.Context()

        with self.assertRaises(SomeError):
            with context.session_manager():
                raise SomeError()

        self._session.commit.assert_not_called()
        self._session.rollback.assert_called_once()
        self._session.close.assert_called_once()
        self._storage.remove_session.assert_called_once()

    def test_context_manager_close_exception(self, engine_factory_mock):
        self._configure_mocks(engine_factory_mock)
        self._session.close.side_effect = SomeError
        context = contexts.Context()

        with context.session_manager():
            pass

        self._session.commit.assert_called_once()
        self._session.close.assert_called_once()
        self._storage.remove_session.assert_called_once()

    def test_context_manager_commit_exception(self, engine_factory_mock):
        self._configure_mocks(engine_factory_mock)
        self._session.commit.side_effect = SomeError
        context = contexts.Context()

        with self.assertRaises(SomeError):
            with context.session_manager():
                pass

        self._session.commit.assert_called_once()
        self._session.rollback.assert_called_once()
        self._session.close.assert_called_once()
        self._storage.remove_session.assert_called_once()

    def test_context_manager_commit_and_rollback_exception(
        self, engine_factory_mock
    ):
        self._configure_mocks(engine_factory_mock)
        self._session.configure_mock(
            **{
                "commit.side_effect": SomeError,
                "rollback.side_effect": SomeError,
            }
        )
        context = contexts.Context()

        with self.assertRaises(SomeError):
            with context.session_manager():
                pass

        self._session.commit.assert_called_once()
        self._session.rollback.assert_called_once()
        self._session.close.assert_called_once()
        self._storage.remove_session.assert_called_once()
