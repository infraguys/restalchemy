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

from http import client as http_client
import logging

from restalchemy.api import middlewares
from restalchemy.common import exceptions as comm_exc
from restalchemy.storage import exceptions as ra_exceptions

UNKNOWN_ERROR_CODE = 10000001


LOG = logging.getLogger(__name__)


def exception2dict(exception):
    code = (
        exception.get_code()
        if hasattr(exception, "get_code")
        else (exception.code if hasattr(exception, "code") else UNKNOWN_ERROR_CODE)
    )
    message = (
        exception.msg
        if hasattr(exception, "msg")
        else (exception.message if hasattr(exception, "message") else str(exception))
    )
    return {
        "type": exception.__class__.__name__,
        "code": code,
        "message": message,
    }


def get_status_code_for_exception(
    exception,
    not_found_exc=(ra_exceptions.RecordNotFound,),
    conflict_exc=(ra_exceptions.ConflictRecords,),
    valid_exc=(comm_exc.ValidationErrorException,),
    common_exc=(comm_exc.RestAlchemyException,),
):
    """Map an exception instance to an HTTP status code.

    Shared between ErrorsHandlerMiddleware (whole-request errors) and
    restalchemy.api.batch.BatchController (per-item errors in a batch), so
    both use the same exception-type-to-status-code rules.
    """
    if isinstance(exception, not_found_exc):
        return http_client.NOT_FOUND
    elif isinstance(exception, conflict_exc):
        return http_client.CONFLICT
    elif isinstance(exception, valid_exc):
        return http_client.BAD_REQUEST
    elif isinstance(exception, common_exc):
        return exception.code
    else:
        return http_client.INTERNAL_SERVER_ERROR


class ErrorsHandlerMiddleware(middlewares.Middleware):
    not_found_exc = (ra_exceptions.RecordNotFound,)
    conflict_exc = (ra_exceptions.ConflictRecords,)
    common_exc = (comm_exc.RestAlchemyException,)
    valid_exc = (comm_exc.ValidationErrorException,)

    def _construct_error_response(self, req, e):
        status = get_status_code_for_exception(
            e,
            not_found_exc=self.not_found_exc,
            conflict_exc=self.conflict_exc,
            valid_exc=self.valid_exc,
            common_exc=self.common_exc,
        )
        return req.ResponseClass(status=status, json=exception2dict(e))

    def process_request(self, req):
        try:
            return req.get_response(self.application)
        except Exception as e:
            resp = self._construct_error_response(req, e)
            if resp.status_code >= 500:
                LOG.exception(
                    "Unknown error has occurred on url: %s %s", req.method, req.url
                )
            return resp
