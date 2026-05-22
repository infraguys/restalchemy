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

import logging

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
        res_mock = mock.MagicMock()
        res_mock.status_code = 200
        res_mock.content_length = 0
        res_mock.body = b"ok"
        request_mock.get_response.return_value = res_mock
        middlew = LoggingMiddleware("application")
        checks = {}
        middlew.logger.setLevel(logging.DEBUG)

        def _check_sanitized_header(msg, *args, **kwargs):
            if "API > " in msg:
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


class LoggingMiddlewareHttpTestCase(base.BaseTestCase):
    def setUp(self):
        super(LoggingMiddlewareHttpTestCase, self).setUp()
        self.middlew = LoggingMiddleware("application")
        self.middlew.logger.setLevel(logging.INFO)

    def test_truncate_body_none(self):
        result = self.middlew._truncate_body(None)
        self.assertIsNone(result)

    def test_truncate_body_small(self):
        result = self.middlew._truncate_body(b"small")
        self.assertEqual(result, "small")

    def test_truncate_body_large(self):
        body = b"x" * 5000
        result = self.middlew._truncate_body(body)
        self.assertTrue(result.endswith("... [%d bytes total]" % 5000))

    def test_truncate_body_bytes_unicode(self):
        body = "test\xc3\xa9\xc3\xa9\xc3\xa9".encode()
        result = self.middlew._truncate_body(body)
        self.assertIsInstance(result, str)

    def test_response_with_exception(self):
        request_mock = mock.MagicMock()
        request_mock.get_response.side_effect = Exception("test")
        request_mock.client_addr = "127.0.0.1"
        request_mock.referer = "-"
        request_mock.user_agent = "test-agent"
        request_mock.method = "GET"
        request_mock.url = "/test"
        request_mock.headers = {}
        request_mock.environ = {}

        with mock.patch.object(logging.Logger, "info") as log_info:
            with self.assertRaises(Exception):
                self.middlew.process_request(request_mock)
            log_info.assert_called()

    def test_response(self):
        res = mock.Mock()
        res.status_code = 200
        res.content_length = 100
        res.body = b"ok"

        request_mock = mock.MagicMock()
        request_mock.get_response.return_value = res
        request_mock.client_addr = "127.0.0.1"
        request_mock.referer = "-"
        request_mock.user_agent = "test-agent"
        request_mock.method = "GET"
        request_mock.url = "/test"
        request_mock.headers = {}
        request_mock.environ = {}

        with mock.patch.object(logging.Logger, "info") as log_info:
            self.middlew.process_request(request_mock)
            log_info.assert_called()

    def test_large_response_body(self):
        res = mock.Mock()
        res.status_code = 500
        res.content_length = 50
        res.body = b"error body"

        request_mock = mock.MagicMock()
        request_mock.get_response.return_value = res
        request_mock.client_addr = "127.0.0.1"
        request_mock.referer = "http://example.com"
        request_mock.user_agent = "test-agent"
        request_mock.method = "POST"
        request_mock.url = "/api/resource"
        request_mock.headers = {}
        request_mock.environ = {}

        with mock.patch.object(logging.Logger, "info") as log_info:
            self.middlew.process_request(request_mock)
            called_args = log_info.call_args[0][0]
            self.assertIn("body=", called_args)
            self.assertIn("error body", called_args)

    def test_get_real_ip_x_forwarded_for(self):
        req = mock.Mock()
        req.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
        ip = self.middlew._get_real_ip(req)
        self.assertEqual(ip, "1.2.3.4")

    def test_get_real_ip_x_real_ip(self):
        req = mock.Mock()
        req.headers = {"X-Real-IP": "9.8.7.6"}
        ip = self.middlew._get_real_ip(req)
        self.assertEqual(ip, "9.8.7.6")

    def test_get_real_ip_fallback(self):
        req = mock.Mock()
        req.headers = {}
        req.client_addr = "127.0.0.1"
        ip = self.middlew._get_real_ip(req)
        self.assertEqual(ip, "127.0.0.1")
