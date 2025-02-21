# Copyright 2019 Eugene Frolov
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

from __future__ import absolute_import

import logging
import re
import sys
import time

from restalchemy.api import middlewares

LOG = logging.getLogger(__name__)


class HttpMetricsMiddleware(middlewares.Middleware):

    def __init__(
        self,
        application,
        path_pattern,
        success_metric_name,
        error_metric_name,
        metric_sender,
    ):
        super(HttpMetricsMiddleware, self).__init__(application)
        self._re = re.compile(path_pattern)
        self._success_metric_name = success_metric_name
        self._error_metric_name = error_metric_name
        self._sender = metric_sender

    def process_request(self, req):
        if self._re.match(req.path) is None:
            return req.get_response(self.application)

        current_time = time.time()
        try:
            res = req.get_response(self.application)
            elapsed = time.time() - current_time
            if res.status_code >= 400:
                self._sender.send_metric(self._error_metric_name, elapsed)
                self._sender.send_metric(
                    "%s.%d" % (self._error_metric_name, res.status_code),
                    elapsed,
                )
            else:
                self._sender.send_metric(self._success_metric_name, elapsed)
            return res
        except Exception:
            self._sender.send_metric(
                "%s.unexpected-error" % self._error_metric_name,
                time.time() - current_time,
            )
            raise
