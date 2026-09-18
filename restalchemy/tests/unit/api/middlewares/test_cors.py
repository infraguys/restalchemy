# Copyright 2026 Genesis Corporation
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

from webob import request

from restalchemy.api.middlewares import cors
from restalchemy.tests.unit import base


def fake_application(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"payload"]


class CorsMiddlewareTestCase(base.BaseTestCase):
    ALLOWED_ORIGIN = "https://example.com"

    def get_middlew(self, allowed_origins=None, **kwargs):
        return cors.CorsMiddleware(
            application=fake_application,
            allowed_origins=allowed_origins or [self.ALLOWED_ORIGIN],
            **kwargs,
        )

    def get_preflight(self, method="POST"):
        req = request.Request.blank("/v1/", method="OPTIONS")
        req.headers["Origin"] = self.ALLOWED_ORIGIN
        req.headers["Access-Control-Request-Method"] = method
        return req

    def test_request_without_origin_is_untouched(self):
        req = request.Request.blank("/v1/")

        res = req.get_response(self.get_middlew())

        self.assertEqual(b"payload", res.body)
        self.assertNotIn("Access-Control-Allow-Origin", res.headers)

    def test_disallowed_origin_gets_no_cors_headers(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = "https://evil.com"

        res = req.get_response(self.get_middlew())

        self.assertEqual(b"payload", res.body)
        self.assertNotIn("Access-Control-Allow-Origin", res.headers)

    def test_every_answer_varies_by_origin(self):
        # A cache must not hand an answer built for one origin, or for no
        # origin at all, to a request that carried another.
        for origin in (None, "https://evil.com", self.ALLOWED_ORIGIN):
            with self.subTest(origin=origin):
                req = request.Request.blank("/v1/")
                if origin is not None:
                    req.headers["Origin"] = origin

                res = req.get_response(self.get_middlew())

                self.assertIn("Origin", res.headers["Vary"])

    def test_allowed_origin_gets_cors_headers(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = self.ALLOWED_ORIGIN

        res = req.get_response(self.get_middlew())

        self.assertEqual(b"payload", res.body)
        self.assertEqual(
            self.ALLOWED_ORIGIN, res.headers["Access-Control-Allow-Origin"]
        )
        self.assertIn("Origin", res.headers["Vary"])

    def test_any_origin_is_echoed_back(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = "https://anywhere.example.net"

        res = req.get_response(self.get_middlew([cors.ANY_ORIGIN]))

        self.assertEqual(
            "https://anywhere.example.net",
            res.headers["Access-Control-Allow-Origin"],
        )

    def test_pagination_and_location_are_exposed_by_default(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = self.ALLOWED_ORIGIN

        res = req.get_response(self.get_middlew())

        exposed = res.headers["Access-Control-Expose-Headers"]
        self.assertIn("Location", exposed)
        self.assertIn("X-Pagination-Marker", exposed)

    def test_exposed_headers_are_configurable(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = self.ALLOWED_ORIGIN

        res = req.get_response(self.get_middlew(exposed_headers=["X-Request-Id"]))

        self.assertEqual("X-Request-Id", res.headers["Access-Control-Expose-Headers"])

    def test_no_exposed_headers_omits_the_header(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = self.ALLOWED_ORIGIN

        res = req.get_response(self.get_middlew(exposed_headers=None))

        self.assertNotIn("Access-Control-Expose-Headers", res.headers)

    def test_nothing_is_exposed_to_a_disallowed_origin(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = "https://evil.com"

        res = req.get_response(self.get_middlew())

        self.assertNotIn("Access-Control-Expose-Headers", res.headers)

    def test_a_configured_origin_is_normalized(self):
        # A browser sends "https://example.com"; the config was written by
        # hand with a trailing slash and a capitalised host.
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = self.ALLOWED_ORIGIN

        res = req.get_response(self.get_middlew(["https://Example.com/"]))

        self.assertEqual(
            self.ALLOWED_ORIGIN, res.headers["Access-Control-Allow-Origin"]
        )

    def test_normalization_does_not_widen_the_allowlist(self):
        req = request.Request.blank("/v1/")
        req.headers["Origin"] = "https://example.com.evil.com"

        res = req.get_response(self.get_middlew(["https://Example.com/"]))

        self.assertNotIn("Access-Control-Allow-Origin", res.headers)

    def test_preflight_is_answered_without_calling_the_application(self):
        req = request.Request.blank("/v1/", method="OPTIONS")
        req.headers["Origin"] = self.ALLOWED_ORIGIN
        req.headers["Access-Control-Request-Method"] = "POST"
        req.headers["Access-Control-Request-Headers"] = "Authorization"

        res = req.get_response(self.get_middlew())

        self.assertEqual(204, res.status_code)
        self.assertEqual(b"", res.body)
        self.assertEqual(
            self.ALLOWED_ORIGIN, res.headers["Access-Control-Allow-Origin"]
        )
        self.assertEqual("POST", res.headers["Access-Control-Allow-Methods"])
        self.assertEqual("Authorization", res.headers["Access-Control-Allow-Headers"])
        self.assertEqual(
            str(cors.PREFLIGHT_MAX_AGE), res.headers["Access-Control-Max-Age"]
        )

    def test_preflight_without_requested_headers(self):
        req = self.get_preflight(method="GET")

        res = req.get_response(self.get_middlew())

        self.assertEqual(204, res.status_code)
        self.assertNotIn("Access-Control-Allow-Headers", res.headers)

    def test_configured_max_age_is_sent(self):
        req = self.get_preflight()

        res = req.get_response(self.get_middlew(preflight_max_age=3600))

        self.assertEqual("3600", res.headers["Access-Control-Max-Age"])

    def test_max_age_none_omits_the_header(self):
        req = self.get_preflight()

        res = req.get_response(self.get_middlew(preflight_max_age=None))

        self.assertEqual(204, res.status_code)
        self.assertNotIn("Access-Control-Max-Age", res.headers)

    def test_plain_options_request_reaches_the_application(self):
        req = request.Request.blank("/v1/", method="OPTIONS")
        req.headers["Origin"] = self.ALLOWED_ORIGIN

        res = req.get_response(self.get_middlew())

        self.assertEqual(b"payload", res.body)
        self.assertEqual(
            self.ALLOWED_ORIGIN, res.headers["Access-Control-Allow-Origin"]
        )
