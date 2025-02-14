# Copyright 2022 Eugene Frolov <eugene@frolov.net.ru>
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

import logging

LOG = logging.getLogger(__name__)


class ResourceSchemaGenerator(object):

    def __init__(self, resource, route):
        super(ResourceSchemaGenerator, self).__init__()
        self._resource = resource
        self._route = route

    @property
    def resource_name(self):
        return self._resource.get_model().__name__

    def resource_method_name(self, method):
        return "{}_{}".format(self.resource_name, method.capitalize())

    def resource_prop_name(self, prop_name):
        return self.resource_name + prop_name.capitalize()

    def get_prop_kwargs(self, name):
        return (
            self._resource.get_model().properties.properties[name].get_kwargs()
        )

    def generate_parameter_object(self, request):
        parameters = {}
        has_id_property = False
        for name, prop in self._resource.get_fields_by_request(request):
            try:
                prop_kwargs = self.get_prop_kwargs(name)
            except KeyError:
                prop_kwargs = {}
            schema = prop.get_type().to_openapi_spec(prop_kwargs)
            try:
                is_id = prop.is_id_property()
            except KeyError:
                is_id = False
            if is_id:
                has_id_property = True
                prop_name = self.resource_prop_name(name)
            else:
                prop_name = prop.api_name
            parameters[prop_name] = {
                "name": prop_name,
                "in": "path" if is_id else "query",
                "schema": schema,
            }
            if is_id:
                parameters[prop_name]["required"] = True
        if not has_id_property:
            try:
                model = self._resource.get_model()
                id_prop_struct = model.get_id_property()
                id_prop = list(id_prop_struct.items())[0]
                name, prop = id_prop
                prop = prop(value=prop._kwargs.get("default", 0))
                try:
                    prop_kwargs = self.get_prop_kwargs(name)
                except KeyError:
                    prop_kwargs = {}
                schema = prop.get_property_type().to_openapi_spec(prop_kwargs)
                prop_name = self.resource_prop_name(name)
                parameters[prop_name] = {
                    "name": prop_name,
                    "in": "path",
                    "schema": schema,
                }
                parameters[prop_name]["required"] = True
            except Exception:
                LOG.exception("Error on generate_parameter_object:")
        return parameters

    def generate_schema_object(self, method):
        return self._resource.generate_schema_object(method)


class Schema(object):
    def __init__(
        self,
        summary=None,
        parameters=None,
        responses=None,
        tags=None,
        request_body=None,
        operation_id=None,
    ):
        self.summary = summary or ""
        self.parameters = parameters or []
        self.responses = responses or {}
        self.tags = tags or []
        self.request_body = request_body
        self.operation_id = operation_id

    @property
    def result(self):
        res = {
            "summary": self.summary,
            "tags": self.tags,
            "parameters": self.parameters,
            "responses": self.responses,
        }
        if self.request_body is not None:
            res["requestBody"] = self.request_body
        if self.operation_id is not None:
            res["operationId"] = self.operation_id
        return res


def extend_schema(
    summary=None,
    parameters=None,
    responses=None,
    tags=None,
    request_body=None,
    operation_id=None,
):
    if parameters and not isinstance(parameters, list):
        raise ValueError("parameters type is not list")
    if responses and not isinstance(responses, dict):
        raise ValueError("responses type is not dict")
    if tags and not isinstance(tags, list):
        raise ValueError("tags type is not list")

    def decorator(f):
        schema = Schema(
            summary=summary,
            parameters=parameters,
            responses=responses,
            tags=tags,
            request_body=request_body,
            operation_id=operation_id,
        )
        f.openapi_schema = schema
        return f

    return decorator
