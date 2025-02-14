# Copyright 2021 George Melikov
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

from restalchemy.api.middlewares.logging import LoggingMiddleware
from restalchemy.tests.unit import base


class LoggingMiddlewareTestCase(base.BaseTestCase):

    def test_sanitize_authorization_header(self):
        request_mock = mock.MagicMock()
        request_mock.headers = {
            "fake_header": "fake_header_value",
            "Authorization": "basic something",
        }
        middlew = LoggingMiddleware("application")
        checks = {}

        def _check_sanitized_header(msg, *args, **kwargs):
            if "API > " in msg:  # test only request logs
                checks["check_run"] = True
                for header in args[1]:
                    if header.startswith("Authorization"):
                        if "something" not in header:
                            checks["Authorization"] = True
                    if header.startswith("fake_header"):
                        if "fake_header_value" in header:
                            checks["fake_header"] = True

        middlew.logger.debug = mock.Mock(side_effect=_check_sanitized_header)

        middlew.process_request(request_mock)

        self.assertTrue(checks["check_run"])
        self.assertTrue(checks["Authorization"])
        self.assertTrue(checks["fake_header"])
        self.assertDictEqual(
            {
                "fake_header": "fake_header_value",
                "Authorization": "basic something",
            },
            request_mock.headers,
        )
