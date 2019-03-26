# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

from restalchemy.storage.sql import engines
from restalchemy.tests.unit import base


class TestEngineTestCase(base.BaseTestCase):

    @mock.patch('mysql.connector.pooling.MySQLConnectionPool')
    def setUp(self, *args):
        super(TestEngineTestCase, self).setUp()
        self._engine = engines.MySQLEngine(
            db_url="mysql://test:test@test/test")

    def tearDown(self):
        super(TestEngineTestCase, self).tearDown()
        del self._engine

    def test_session_manager_session_as_argument(self):
        session = mock.Mock()

        with self._engine.session_manager(session=session) as s:

            self.assertEqual(s, session)

    def test_session_manager_session_as_thread_storage(self):
        session = mock.Mock()

        with mock.patch.object(self._engine, '_get_session_from_storage',
                               return_value=session):
            with self._engine.session_manager() as s:

                self.assertEqual(s, session)

    def test_session_manager_get_new_session(self):
        session = mock.Mock()

        with mock.patch.object(self._engine, 'get_session',
                               return_value=session):
            with self._engine.session_manager() as s:

                self.assertEqual(s, session)
