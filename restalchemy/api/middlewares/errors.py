# Copyright 2018 Eugene Frolov
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
from http import client as http_client

from restalchemy.api import middlewares
from restalchemy.common import exceptions as comm_exc
from restalchemy.storage import exceptions as ra_exceptions

UNKNOWN_ERROR_CODE = 10000001


LOG = logging.getLogger(__name__)


def exception2dict(exception):
    code = (
        exception.get_code()
        if hasattr(exception, "get_code")
        else (
            exception.code
            if hasattr(exception, "code")
            else UNKNOWN_ERROR_CODE
        )
    )
    message = (
        exception.msg
        if hasattr(exception, "msg")
        else (
            exception.message
            if hasattr(exception, "message")
            else str(exception)
        )
    )
    return {
        "type": exception.__class__.__name__,
        "code": code,
        "message": message,
    }


class ErrorsHandlerMiddleware(middlewares.Middleware):

    not_found_exc = (ra_exceptions.RecordNotFound,)
    conflict_exc = (ra_exceptions.ConflictRecords,)
    common_exc = (comm_exc.RestAlchemyException,)
    valid_exc = (comm_exc.ValidationErrorException,)

    def _construct_error_response(self, req, e):
        if isinstance(e, self.not_found_exc):
            return req.ResponseClass(
                status=http_client.NOT_FOUND, json=exception2dict(e)
            )
        elif isinstance(e, self.conflict_exc):
            return req.ResponseClass(
                status=http_client.CONFLICT, json=exception2dict(e)
            )
        elif isinstance(e, self.valid_exc):
            return req.ResponseClass(
                status=http_client.BAD_REQUEST, json=exception2dict(e)
            )
        elif isinstance(e, self.common_exc):
            return req.ResponseClass(status=e.code, json=exception2dict(e))
        else:
            return req.ResponseClass(
                status=http_client.INTERNAL_SERVER_ERROR,
                json=exception2dict(e),
            )

    def process_request(self, req):
        try:
            return req.get_response(self.application)
        except Exception as e:
            LOG.exception(
                "Unknown error has occurred on url: %s %s", req.method, req.url
            )
            return self._construct_error_response(req, e)
