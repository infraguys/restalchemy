# Copyright 2026 George Melikov
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

import unittest

import mock
import webob

from restalchemy.api import batch
from restalchemy.common import exceptions as exc


def _fake_response(status_code, body=b""):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.body = body
    return resp


class TestBuildSubRequest(unittest.TestCase):
    def setUp(self):
        super(TestBuildSubRequest, self).setUp()
        self._outer_req = webob.Request.blank("/batch", base_url="http://example.com")
        self._controller = batch.BatchController(request=self._outer_req)

    def test_sets_method_path_and_body(self):
        sub_req = self._controller._build_sub_request(
            {"method": "POST", "path": "/v1/foos/", "body": {"name": "a"}}
        )

        self.assertEqual(sub_req.method, "POST")
        self.assertEqual(sub_req.path_info, "/v1/foos/")
        self.assertEqual(sub_req.body, b'{"name":"a"}')
        self.assertEqual(sub_req.content_type, "application/json")

    def test_empty_body_for_missing_body(self):
        sub_req = self._controller._build_sub_request(
            {"method": "GET", "path": "/v1/foos/"}
        )

        self.assertEqual(sub_req.body, b"")

    def test_splits_query_string_from_path(self):
        sub_req = self._controller._build_sub_request(
            {"method": "GET", "path": "/v1/foos/?name=x&other=y"}
        )

        self.assertEqual(sub_req.path_info, "/v1/foos/")
        self.assertEqual(sub_req.query_string, "name=x&other=y")
        self.assertEqual(sub_req.params.get("name"), "x")

    def test_marks_environ_as_in_batch(self):
        sub_req = self._controller._build_sub_request(
            {"method": "GET", "path": "/v1/foos/"}
        )

        self.assertTrue(sub_req.environ[batch.BatchController.__in_batch_environ_key__])

    def test_adhoc_attrs_are_decoupled_from_outer_request(self):
        """Regression test: webob stores req.context/req.application/etc in
        environ["webob.adhoc_attrs"], and Request.copy() only shallow-copies
        environ, so without an explicit reset a sub-request's dispatch would
        silently overwrite the outer /batch request's own adhoc attributes
        (and any other sub-request's), since they'd share the same dict.
        """
        self._outer_req.context = "outer-context"

        sub_req_1 = self._controller._build_sub_request(
            {"method": "GET", "path": "/v1/foos/"}
        )
        sub_req_2 = self._controller._build_sub_request(
            {"method": "GET", "path": "/v1/bars/"}
        )

        self.assertIsNot(
            sub_req_1.environ["webob.adhoc_attrs"],
            self._outer_req.environ["webob.adhoc_attrs"],
        )
        self.assertIsNot(
            sub_req_1.environ["webob.adhoc_attrs"],
            sub_req_2.environ["webob.adhoc_attrs"],
        )

        sub_req_1.api_context = "sub-1-api-context"
        sub_req_2.api_context = "sub-2-api-context"

        self.assertEqual(sub_req_1.api_context, "sub-1-api-context")
        self.assertEqual(sub_req_2.api_context, "sub-2-api-context")
        self.assertFalse(hasattr(self._outer_req, "api_context"))
        self.assertEqual(self._outer_req.context, "outer-context")

    def test_custom_headers_are_applied(self):
        sub_req = self._controller._build_sub_request(
            {
                "method": "GET",
                "path": "/v1/foos/",
                "headers": {"X-Custom": "value"},
            }
        )

        self.assertEqual(sub_req.headers.get("X-Custom"), "value")


class TestCreate(unittest.TestCase):
    def setUp(self):
        super(TestCreate, self).setUp()
        self._outer_req = webob.Request.blank("/batch", base_url="http://example.com")
        self._outer_req.application = mock.Mock()
        self._controller = batch.BatchController(request=self._outer_req)

    def test_nested_batch_is_rejected(self):
        self._outer_req.environ[batch.BatchController.__in_batch_environ_key__] = True

        self.assertRaises(
            exc.NestedBatchNotAllowed,
            self._controller.create,
            requests=[],
        )

    def test_requests_must_be_a_list(self):
        self.assertRaises(
            exc.ParseError,
            self._controller.create,
            requests={"method": "GET", "path": "/v1/foos/"},
        )

    def test_batch_size_limit_is_enforced(self):
        requests = [{"method": "GET", "path": "/v1/foos/"}] * (
            self._controller.__max_batch_size__ + 1
        )

        self.assertRaises(
            exc.BatchSizeLimitExceeded,
            self._controller.create,
            requests=requests,
        )

    @mock.patch.object(webob.Request, "get_response")
    def test_dispatches_through_outer_wsgi_app_when_recorded(self, get_response_mock):
        """A middleware-wrapped app records itself as
        environ["restalchemy.wsgi_app"] (see Middleware.__call__) -- batch
        must replay sub-requests through *that*, not the bare inner
        WSGIApp, so per-route middleware (auth, policy, rate limiting,
        retry) still applies to each item.
        """
        outer_app = mock.Mock()
        self._outer_req.environ["restalchemy.wsgi_app"] = outer_app
        get_response_mock.return_value = _fake_response(200, b"{}")

        self._controller.create(requests=[{"method": "GET", "path": "/v1/foos/1"}])

        used_app = get_response_mock.call_args[0][0]
        self.assertIs(used_app, outer_app)
        self.assertIsNot(used_app, self._outer_req.application)

    @mock.patch.object(webob.Request, "get_response")
    def test_falls_back_to_inner_app_without_middlewares(self, get_response_mock):
        get_response_mock.return_value = _fake_response(200, b"{}")

        self._controller.create(requests=[{"method": "GET", "path": "/v1/foos/1"}])

        used_app = get_response_mock.call_args[0][0]
        self.assertIs(used_app, self._outer_req.application)

    @mock.patch.object(webob.Request, "get_response")
    def test_best_effort_continues_after_item_failure(self, get_response_mock):
        get_response_mock.side_effect = [
            _fake_response(200, b'{"ok": true}'),
            exc.RestAlchemyException(),
            _fake_response(200, b'{"ok": true}'),
        ]

        result = self._controller.create(
            requests=[
                {"method": "GET", "path": "/v1/foos/1"},
                {"method": "GET", "path": "/v1/foos/2"},
                {"method": "GET", "path": "/v1/foos/3"},
            ],
        )

        self.assertEqual(3, len(result))
        self.assertEqual(200, result[0]["status"])
        self.assertEqual(500, result[1]["status"])
        self.assertEqual(200, result[2]["status"])

    def test_malformed_item_fails_only_that_item(self):
        """_build_sub_request runs inside the per-item try/except too, so a
        malformed item (missing "method"/"path") produces a failed entry
        for just that item instead of aborting the whole batch.
        """
        with mock.patch.object(webob.Request, "get_response") as get_response_mock:
            get_response_mock.return_value = _fake_response(200, b'{"ok": true}')

            result = self._controller.create(
                requests=[
                    {"path": "/v1/foos/1"},  # missing "method"
                    {"method": "GET", "path": "/v1/foos/2"},
                ],
            )

        self.assertEqual(2, len(result))
        self.assertEqual(500, result[0]["status"])
        self.assertEqual(200, result[1]["status"])
