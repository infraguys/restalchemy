# Copyright 2023 v.burygin
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

import mock

import http.client as http_client

from restalchemy.api.middlewares import errors
from restalchemy.common import exceptions as comm_exc
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.tests.unit import base

from webob import request


class FakeResponse(object):
    def __init__(self, status, json, **kwargs):
        self.status = status
        self.json = json


class FakeConflictRecords(ra_exceptions.ConflictRecords):
    message = "Duplicate parameters"


class FakeRecordNotFound(ra_exceptions.RecordNotFound):
    message = "Can't found record in storage"


class ErrorsHandlerMiddlewareTestCase(base.BaseTestCase):
    middlew = errors.ErrorsHandlerMiddleware("application")

    def test_response_restalchemy_exc(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = comm_exc.RestAlchemyException
        request_mock.ResponseClass = FakeResponse
        response = self.middlew.process_request(request_mock)

        assert response.status == comm_exc.RestAlchemyException.code

    def test_response_validation_error(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = (
            comm_exc.ValidationErrorException
        )
        request_mock.ResponseClass = FakeResponse
        response = self.middlew.process_request(request_mock)

        assert response.status == http_client.BAD_REQUEST

    def test_response_conflict_record(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = FakeConflictRecords
        request_mock.ResponseClass = FakeResponse
        response = self.middlew.process_request(request_mock)

        assert response.status == http_client.CONFLICT

    def test_response_not_found(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = FakeRecordNotFound
        request_mock.ResponseClass = FakeResponse
        response = self.middlew.process_request(request_mock)

        assert response.status == http_client.NOT_FOUND

    def test_absent_message_attr_for_base_exceptions(self):
        request_mock = mock.Mock(spec=request.Request)
        request_mock.get_response.side_effect = TypeError
        request_mock.ResponseClass = FakeResponse
        response = self.middlew.process_request(request_mock)

        assert response.status == http_client.INTERNAL_SERVER_ERROR
