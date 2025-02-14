# Copyright 2023 Aleksandr Bochkarev
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

from restalchemy.api.middlewares import retry_on_error
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.tests.unit import base

from webob import request


class FakeDeadLock(ra_exceptions.DeadLock):
    message = "Deadlock is found"


class FakeRecordNotFound(ra_exceptions.RecordNotFound):
    message = "Can't found record in storage"


class RetryOnErrorMiddlewareTestCase(base.BaseTestCase):
    call_count = 3
    app = "application"

    def get_middlew(self, exc=FakeDeadLock, call_count=None):
        return retry_on_error.RetryOnErrorsMiddleware(
            self.app, exc, call_count or self.call_count
        )

    def test_retry_on_deadlock_exc(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = FakeDeadLock
        with self.assertRaises(ra_exceptions.DeadLock):
            self.get_middlew().process_request(request_mock)
        request_mock.get_response.assert_called_with(self.app)
        self.assertEqual(self.call_count, request_mock.get_response.call_count)

    def test_retry_on_record_not_found_exc(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = FakeRecordNotFound
        with self.assertRaises(ra_exceptions.RecordNotFound):
            self.get_middlew().process_request(request_mock)
        request_mock.get_response.assert_called_with(self.app)
        self.assertEqual(1, request_mock.get_response.call_count)

    def test_retry_when_no_exc(self):
        request_mock = mock.Mock(spec=request.Request)
        response = self.get_middlew().process_request(request_mock)
        self.assertIsNotNone(response)
        request_mock.get_response.assert_called_with(self.app)
        self.assertEqual(1, request_mock.get_response.call_count)

    def test_retry_when_retry_count_less_0(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = FakeDeadLock
        with self.assertRaises(ra_exceptions.DeadLock):
            self.get_middlew(call_count=-1).process_request(request_mock)
        request_mock.get_response.assert_called_with(self.app)
        self.assertEqual(1, request_mock.get_response.call_count)
