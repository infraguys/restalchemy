# Copyright 2021 Eugene Frolov
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

from restalchemy.api import middlewares

LOG = logging.getLogger(__name__)


# USE IT BEFORE CONTEXT MIDDLEWARE!
class RetryOnErrorsMiddleware(middlewares.Middleware):

    def __init__(self, application, exceptions, max_retry=3):
        self._exceptions = exceptions
        self._max_retry = max_retry if max_retry > 0 else 1
        super(RetryOnErrorsMiddleware, self).__init__(application)

    def process_request(self, req):
        retry_count = 0
        while True:
            retry_count += 1
            try:
                return req.get_response(self.application)
            except self._exceptions as e:
                LOG.warning(
                    "Unable to process request: %d/%d %s",
                    retry_count,
                    self._max_retry,
                    e,
                )
                if retry_count >= self._max_retry:
                    raise
