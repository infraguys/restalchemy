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

import datetime
import logging

from restalchemy.api import middlewares


class Http500FakeResponse(object):
    def __init__(self, content_length=0, status_code=500):
        self.content_length = content_length
        self.status_code = status_code


class LoggingHttpMiddleware(middlewares.Middleware):
    """API HTTP logging middleware."""

    def __init__(self, application, logger_name=__name__):
        super(LoggingHttpMiddleware, self).__init__(application)
        self.logger = logging.getLogger(logger_name)

    @staticmethod
    def _make_message(start, req, res):
        referer = req.referer or "-"
        duration = datetime.datetime.now() - start
        td_ms = int(duration.total_seconds() * 1000)

        return '%s "%s %s" %s %s "%s" "%s" %s' % (
            req.client_addr,
            req.method,
            req.url,
            res.status_code,
            res.content_length,
            referer,
            req.user_agent,
            td_ms,
        )

    def process_request(self, req):
        start = datetime.datetime.now()

        try:
            res = req.get_response(self.application)
        except Exception:
            res = Http500FakeResponse()
            raise
        else:
            return res
        finally:
            msg = self._make_message(start, req, res)
            self.logger.info(msg)
