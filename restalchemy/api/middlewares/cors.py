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


class CorsMiddleware(middlewares.Middleware):
    """Answers CORS preflights and adds CORS headers to browser responses.

    Attach the middleware only when allowed origins are configured, so that
    an API stays same-origin only by default. Place it outside the
    authentication and error handling middlewares: preflights are answered
    before authentication runs and error responses keep their CORS headers.

    ``Access-Control-Allow-Credentials`` and ``Access-Control-Expose-Headers``
    are deliberately left out: emitting the former next to a ``*`` allowlist
    would let any site read authenticated responses.
    """

    def __init__(self, application, allowed_origins):
        super().__init__(application)
        self._allowed_origins = set(allowed_origins)

    @dec.wsgify
    def __call__(self, req):
        origin = req.headers.get("Origin")
        if origin is None or not self._is_allowed(origin):
            return req.get_response(self.application)

        if self._is_preflight(req):
            response = self._build_preflight_response(req)
        else:
            response = req.get_response(self.application)

        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers.add("Vary", "Origin")
        return response

    def _is_allowed(self, origin):
        return ANY_ORIGIN in self._allowed_origins or origin in self._allowed_origins

    @staticmethod
    def _is_preflight(req):
        return (
            req.method == "OPTIONS" and "Access-Control-Request-Method" in req.headers
        )

    @staticmethod
    def _build_preflight_response(req):
        # A preflight carries no credentials, so it is answered here instead
        # of being rejected by the authentication middleware below.
        response = req.ResponseClass(status=http_client.NO_CONTENT)
        response.headers["Access-Control-Allow-Methods"] = req.headers[
            "Access-Control-Request-Method"
        ]
        requested_headers = req.headers.get("Access-Control-Request-Headers")
        if requested_headers:
            response.headers["Access-Control-Allow-Headers"] = requested_headers
        response.headers["Access-Control-Max-Age"] = str(PREFLIGHT_MAX_AGE)
        return response
