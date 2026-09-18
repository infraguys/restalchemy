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

from http import client as http_client

from webob import dec

from restalchemy.api import middlewares

ANY_ORIGIN = "*"
PREFLIGHT_MAX_AGE = 600
# Response headers a browser client needs to drive this API: the created
# resource's URL, and the marker that asks for the next page of a collection.
EXPOSED_HEADERS = ("Location", "X-Pagination-Limit", "X-Pagination-Marker")


class CorsMiddleware(middlewares.Middleware):
    """Answers CORS preflights and adds CORS headers to browser responses.

    Attach the middleware only when allowed origins are configured, so that
    an API stays same-origin only by default. Place it outside the
    authentication and error handling middlewares: preflights are answered
    before authentication runs and error responses keep their CORS headers.

    ``Access-Control-Allow-Credentials`` is deliberately left out: emitting it
    next to a ``*`` allowlist would let any site read authenticated responses.

    :param allowed_origins: origins a browser may call the API from. ``*``
        allows any origin.
    :param preflight_max_age: how many seconds a browser may cache a preflight
        answer, sent as ``Access-Control-Max-Age``. Pass ``None`` to omit the
        header and leave the browser on its own short default.
    :param exposed_headers: response headers a browser client may read, sent
        as ``Access-Control-Expose-Headers``. Only the CORS-safelisted headers
        are readable without it. Pass an empty value to expose nothing.
    """

    def __init__(
        self,
        application,
        allowed_origins,
        preflight_max_age=PREFLIGHT_MAX_AGE,
        exposed_headers=EXPOSED_HEADERS,
    ):
        super().__init__(application)
        self._allowed_origins = {
            self._normalize_origin(origin) for origin in allowed_origins
        }
        self._preflight_max_age = preflight_max_age
        self._exposed_headers = ", ".join(exposed_headers or ())

    @dec.wsgify
    def __call__(self, req):
        origin = req.headers.get("Origin")
        if origin is None or not self._is_allowed(origin):
            response = req.get_response(self.application)
        elif self._is_preflight(req):
            response = self._build_preflight_response(req, origin)
        else:
            response = self._build_cross_origin_response(req, origin)

        # The answer depends on Origin on every path above, including the one
        # that adds no CORS headers at all, so no cache may hand this response
        # to a request that carried a different origin.
        response.headers.add("Vary", "Origin")
        return response

    def _is_allowed(self, origin):
        if ANY_ORIGIN in self._allowed_origins:
            return True
        return self._normalize_origin(origin) in self._allowed_origins

    @staticmethod
    def _normalize_origin(origin):
        # A browser sends a serialized origin: lowercase scheme and host, no
        # trailing slash. Meet a hand-written config value halfway, so that
        # "https://Console.Example.com/" does not silently allow nothing.
        return origin.strip().rstrip("/").lower()

    @staticmethod
    def _is_preflight(req):
        return (
            req.method == "OPTIONS" and "Access-Control-Request-Method" in req.headers
        )

    def _build_cross_origin_response(self, req, origin):
        response = req.get_response(self.application)
        response.headers["Access-Control-Allow-Origin"] = origin
        if self._exposed_headers:
            response.headers["Access-Control-Expose-Headers"] = self._exposed_headers
        return response

    def _build_preflight_response(self, req, origin):
        # A preflight carries no credentials, so it is answered here instead
        # of being rejected by the authentication middleware below.
        response = req.ResponseClass(status=http_client.NO_CONTENT)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = req.headers[
            "Access-Control-Request-Method"
        ]
        requested_headers = req.headers.get("Access-Control-Request-Headers")
        if requested_headers:
            response.headers["Access-Control-Allow-Headers"] = requested_headers
        if self._preflight_max_age is not None:
            response.headers["Access-Control-Max-Age"] = str(self._preflight_max_age)
        return response
