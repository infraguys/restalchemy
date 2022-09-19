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
        return self._resource.get_model().properties.properties[
            name].get_kwargs()

    def generate_parameter_object(self, request):
        parameters = {}
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
        return parameters

    def generate_schema_object(self, method):
        properties = {}
        required = []
        for name, prop in self._resource.get_fields_by_method(method):
            try:
                prop_kwargs = self.get_prop_kwargs(name)
            except KeyError:
                prop_kwargs = {}
            if prop.is_public():
                properties[prop.api_name] = prop.get_type().to_openapi_spec(
                    prop_kwargs)
            if prop_kwargs.get("required"):
                required.append(name)
        spec = {
            "type": "object",
            "properties": properties,
        }
        if required:
            spec["required"] = required
        return spec


class Schema(object):
    def __init__(self,
                 summary=None,
                 parameters=None,
                 responses=None,
                 tags=None,
                 ):
        self.summary = summary or ""
        self.parameters = parameters or []
        self.responses = responses or {}
        self.tags = tags or []

    @property
    def result(self):
        return {
            "summary": self.summary,
            "tags": self.tags,
            "parameters": self.parameters,
            "responses": self.responses
        }


def extend_schema(
        summary=None,
        parameters=None,
        responses=None,
        tags=None,
):
    if parameters and not isinstance(parameters, list):
        raise ValueError("parameters type is not list")
    if responses and not isinstance(responses, dict):
        raise ValueError("responses type is not dict")
    if tags and not isinstance(parameters, list):
        raise ValueError("tags type is not list")

    def decorator(f):
        schema = Schema(summary=summary,
                        parameters=parameters,
                        responses=responses,
                        tags=tags)
        f.openapi_schema = schema
        return f

    return decorator
