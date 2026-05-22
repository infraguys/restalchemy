# Copyright (c) 2025 Genesis Corporation
# Copyright (c) 2014 Eugene Frolov <efrolov@mirantis.com>
# Copyright (c) 2022 George Melikov
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
import time
import traceback

from restalchemy.api import middlewares


class LoggingMiddleware(middlewares.Middleware):
    """API logging middleware.

    In DEBUG mode: logs full request/response details.
    In INFO mode: logs in nginx-like format, includes response body
    for status codes > 300.
    """

    SENSITIVE_HEADERS = frozenset(("AUTHORIZATION",))
    MAX_BODY_SIZE = 4096

    def _truncate_body(self, body, max_size=None):
        if max_size is None:
            max_size = self.MAX_BODY_SIZE
        if body is None:
            return None
        total_size = len(body)
        if isinstance(body, bytes):
            body = body[:max_size].decode("utf-8", "replace")
        if total_size > max_size:
            return body + "... [%d bytes total]" % total_size
        return body

    def __init__(self, application, logger_name=__name__):
        super(LoggingMiddleware, self).__init__(application)
        self.logger = logging.getLogger(logger_name)

    def process_request(self, req):
        start_s = time.perf_counter()

        if self.logger.isEnabledFor(logging.DEBUG):
            return self._process_debug(req, start_s)
        if self.logger.isEnabledFor(logging.INFO):
            return self._process_info(req, start_s)
        return req.get_response(self.application)

    def _process_debug(self, req, start_s):
        req_chunk = "%s %s" % (req.method, req.url)

        self.logger.debug(
            "API > %s headers=%s body=%r",
            req_chunk,
            self._sanitize_headers(req.headers),
            self._truncate_body(req.body),
        )

        try:
            res = self._process_info(req, start_s)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            e_file, e_lineno, e_fn, e_line = tb[-1] if tb else ("-", "-", "-", "-")
            self.logger.error(
                "API Error >< %s %s %s %s:%s:%s> %s",
                req_chunk,
                type(e),
                e,
                e_file,
                e_lineno,
                e_fn,
                e_line,
            )
            raise

        self.logger.debug(
            "API < %s %s headers=%s body=%r",
            res.status_code,
            req_chunk,
            self._sanitize_headers(res.headers),
            self._truncate_body(res.body),
        )
        return res

    def _process_info(self, req, start_s):
        try:
            res = req.get_response(self.application)
        except Exception:
            self.logger.info(
                self._format_nginx_log(req, 500, 0, None, self._duration_ms(start_s))
            )
            raise

        if res.status_code > 300 and res.body:
            body = self._truncate_body(res.body)
        else:
            body = None

        self.logger.info(
            self._format_nginx_log(
                req,
                res.status_code,
                res.content_length,
                body,
                self._duration_ms(start_s),
            )
        )
        return res

    def _get_real_ip(self, req):
        xff = req.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",", 1)[0].strip()
        xri = req.headers.get("X-Real-IP")
        if xri:
            return xri
        return req.client_addr or "-"

    def _format_nginx_log(self, req, status, size, body, duration_ms):
        proto = req.environ.get("SERVER_PROTOCOL", "HTTP/1.1") or "HTTP/1.1"
        if isinstance(proto, bytes):
            proto = proto.decode("utf-8", "replace")
        protocol = proto.strip()

        msg = (
            f'RESP: {self._get_real_ip(req)} "{req.method} {req.url}" '
            f'{protocol} {status} {size} "{req.referer or "-"}" '
            f'"{req.user_agent or "-"}" {duration_ms}ms'
            f"{f' body={body!r}' if body else ''}"
        )

        return msg

    def _duration_ms(self, start_s):
        return int((time.perf_counter() - start_s) * 1000)

    def _sanitize_headers(self, headers):
        return [
            "%s: %s" % (h, "***" if h.upper() in self.SENSITIVE_HEADERS else v)
            for h, v in headers.items()
        ]
