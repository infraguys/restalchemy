# Copyright (c) 2014 Eugene Frolov <efrolov@mirantis.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import logging
import sys
import traceback

from restalchemy.api import middlewares


LOG = logging.getLogger(__name__)


class LoggingMiddleware(middlewares.Middleware):
    """API logging middleware."""

    SENSITIVE_HEADERS = {
        "AUTHORIZATION",
    }

    def __init__(self, application, logger_name=__name__):
        super(LoggingMiddleware, self).__init__(application)
        self.logger = logging.getLogger(logger_name)

    def process_request(self, req):
        req_chunk = self._request_chunk(req)
        sanitized_headers = self._sanitize_headers(req.headers)
        self.logger.debug(
            "API > %s headers=%s body=%r",
            req_chunk,
            self._headers_chunk(sanitized_headers),
            req.body,
        )
        try:
            res = req.get_response(self.application)
            # XXX(Eugeny Flolov):
            # :py:method:`middlewares.ContextMiddleware#process_response`
            # unreachable if
            # :py:method:`middlewares.ContextMiddleware#process_request`
            # returns response.
            self.logger.debug(
                "API < %s %s headers=%s body=%r",
                res.status_code,
                self._request_chunk(req),
                self._headers_chunk(res.headers),
                res.body,
            )
            return res
        except Exception:
            e_type, e_value, e_tb = sys.exc_info()
            e_file, e_lineno, e_fn, e_line = traceback.extract_tb(e_tb)[-1]
            self.logger.error(
                "API Error %s %s %s %s:%s:%s> %s",
                req_chunk,
                e_type,
                e_value,
                e_file,
                e_lineno,
                e_fn,
                e_line,
            )
            raise

    @staticmethod
    def _request_chunk(req):
        return "%s %s" % (req.method, req.url)

    @staticmethod
    def _headers_chunk(headers):
        return ["%s: %s" % (h, headers[h]) for h in headers]

    def _sanitize_headers(self, headers):
        def _sanitized(header, header_value):
            if str(header).upper() in self.SENSITIVE_HEADERS:
                return "***"
            return header_value

        return {k: _sanitized(k, v) for k, v in headers.items()}
