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

import logging
from unittest import mock
from unittest.mock import patch

from mysql.connector import errors
from psycopg import errors as pg_errors
import pytest

from restalchemy.storage import exceptions as exc
from restalchemy.storage.sql import sessions
from restalchemy.tests.unit import base


@pytest.mark.parametrize(
    "session_class", [sessions.PgSQLSession, sessions.MySQLSession]
)
@pytest.mark.parametrize("batch", [False, True], ids=["single", "batch"])
@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO], ids=["debug", "info"])
@pytest.mark.parametrize("failure", [False, True], ids=["success", "failure"])
def test_bound_values_are_not_logged(session_class, batch, level, failure, caplog):
    engine = mock.Mock(db_name="test_database")
    session = session_class(engine)
    statement = "INSERT INTO test_payloads (payload) VALUES (%s)"
    marker = "synthetic-private-value"
    payload = {"registration_token": marker, "nested": {"password": marker}}
    values = [(payload,), (payload,)] if batch else (payload,)
    execute = session.execute_many if batch else session.execute
    cursor_execute = session._cursor.executemany if batch else session._cursor.execute
    error = (
        pg_errors.CheckViolation(marker)
        if session_class is sessions.PgSQLSession
        else errors.DatabaseError(marker, errno=3819)
    )
    if failure:
        cursor_execute.side_effect = error

    with caplog.at_level(level, logger=sessions.LOG.name):
        if failure:
            with pytest.raises(type(error)) as caught:
                execute(statement, values)
            assert caught.value is error
        else:
            assert execute(statement, values) is session._cursor

    cursor_execute.assert_called_once_with(statement, values)
    assert cursor_execute.call_args.args[1] is values
    assert marker not in caplog.text
    # Handlers may serialize unformatted arguments instead of getMessage().
    assert marker not in repr([record.args for record in caplog.records])
    if level == logging.DEBUG:
        assert len(caplog.records) == 1
        assert statement in caplog.text
        assert engine.db_name in caplog.text
        assert (
            "Execute batch statement" if batch else "Execute statement"
        ) in caplog.text
    else:
        assert not caplog.records


@pytest.mark.parametrize(
    "session_class", [sessions.PgSQLSession, sessions.MySQLSession]
)
def test_execute_without_bound_values(session_class, caplog):
    session = session_class(mock.Mock(db_name="test_database"))
    with caplog.at_level(logging.DEBUG, logger=sessions.LOG.name):
        assert session.execute("SELECT 1") is session._cursor
    session._cursor.execute.assert_called_once_with("SELECT 1", None)
    assert "SELECT 1" in caplog.text


@pytest.mark.parametrize(
    "session_class", [sessions.PgSQLSession, sessions.MySQLSession]
)
def test_batch_logging_does_not_inspect_values(session_class, caplog):
    session = session_class(mock.Mock(db_name="test_database"))

    class UninspectableValues:
        def __repr__(self):
            raise AssertionError("Values must not be formatted")

        def __iter__(self):
            raise AssertionError("Logging must not consume batch values")

        def __len__(self):
            raise AssertionError("Logging must not count batch values")

    values = UninspectableValues()
    with caplog.at_level(logging.DEBUG, logger=sessions.LOG.name):
        session.execute_many("INSERT INTO test_payloads VALUES (%s)", values)
    session._cursor.executemany.assert_called_once_with(
        "INSERT INTO test_payloads VALUES (%s)", values
    )


class TestLocalThreadStorage(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        self._storage = sessions.SessionThreadStorage()

    def tearDown(self):
        super().tearDown()
        self._storage.remove_session()
        del self._storage

    def test_store_session(self):
        session = mock.Mock()

        self.assertEqual(self._storage.store_session(session), session)
        self.assertEqual(self._storage.get_session(), session)

    def test_store_session_conflict_exception(self):
        session = mock.Mock()

        with patch.object(self._storage, "get_session", return_value=session):
            self.assertRaises(
                sessions.SessionConflict, self._storage.store_session, session
            )

    def test_store_session_conflict_exception_with_two_instance(self):
        instance_one = sessions.SessionThreadStorage()
        instance_two = sessions.SessionThreadStorage()
        session1 = mock.Mock()
        session2 = mock.Mock()

        instance_one.store_session(session1)

        with self.assertRaises(sessions.SessionConflict):
            instance_two.store_session(session2)

    def test_get_session_not_found_exception(self):

        self.assertRaises(sessions.SessionNotFound, self._storage.get_session)

    def test_get_session(self):
        session = mock.Mock()
        self._storage._storage.session = session

        self.assertEqual(self._storage.get_session(), session)

    def test_pop_session(self):
        session = mock.Mock()
        self._storage._storage.session = session

        result = self._storage.pop_session()

        self.assertEqual(result, session)
        self.assertIsNone(self._storage._storage.session)

    def test_execute_when_deadlock_raises(self):
        mock_execute = mock.Mock()
        mock_execute.execute.side_effect = errors.DatabaseError(
            "deadlock", errno=1213, sqlstate=1213
        )
        mock_cursor = mock.Mock()
        mock_cursor.cursor.return_value = mock_execute
        mock_engine = mock.Mock()
        mock_engine.get_connection.return_value = mock_cursor
        session = sessions.MySQLSession(mock_engine)
        with self.assertRaises(exc.DeadLock) as ctx:
            session.execute("update foo set bar = 'baz'")
        self.assertEqual(
            "Deadlock found when trying to get lock. Original message: deadlock",
            str(ctx.exception),
        )

    def test_execute_when_unknown_exc_raises(self):
        mock_execute = mock.Mock()
        mock_execute.execute.side_effect = errors.DatabaseError(
            "error", errno=1062, sqlstate=1062
        )
        mock_cursor = mock.Mock()
        mock_cursor.cursor.return_value = mock_execute
        mock_engine = mock.Mock()
        mock_engine.get_connection.return_value = mock_cursor
        session = sessions.MySQLSession(mock_engine)
        with self.assertRaises(errors.DatabaseError) as ctx:
            session.execute("update foo set bar = 'baz'")
        self.assertEqual("1062 (1062): error", str(ctx.exception))
