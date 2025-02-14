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
from mock import patch

from mysql.connector import errors
from restalchemy.storage import exceptions as exc
from restalchemy.storage.sql import sessions
from restalchemy.tests.unit import base


class TestLocalThreadStorage(base.BaseTestCase):

    def setUp(self):
        super(TestLocalThreadStorage, self).setUp()
        self._storage = sessions.SessionThreadStorage()

    def tearDown(self):
        super(TestLocalThreadStorage, self).tearDown()
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
            "Deadlock found when trying to get lock. "
            "Original message: deadlock",
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
