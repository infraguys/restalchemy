# Copyright 2022 George Melikov
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
import mock

from restalchemy.api.middlewares import logging_http
from restalchemy.common import exceptions
from restalchemy.tests.unit import base

from webob import request


class LoggingHttpMiddlewareTestCase(base.BaseTestCase):
    middlew = logging_http.LoggingHttpMiddleware("application")

    def test_response_with_exception(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = exceptions.RestAlchemyException

        exc = exceptions.RestAlchemyException

        with mock.patch.object(logging.Logger, "info") as log_info:
            with self.assertRaises(exc):
                self.middlew.process_request(request_mock)
            log_info.assert_called()

    def test_response(self):
        res = logging_http.Http500FakeResponse(status_code=200)

        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.return_value = res

        with mock.patch.object(logging.Logger, "info") as log_info:
            self.middlew.process_request(request_mock)
            log_info.assert_called()
