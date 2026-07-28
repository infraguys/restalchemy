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

import json
import logging
import typing

from restalchemy.api import constants as c

LOG = logging.getLogger(__name__)

# Order in which <Model>_<Method> schemas are considered when several methods
# turn out to produce the same body: the first one present becomes the schema
# that actually carries the body, the rest become $ref aliases to it.
SCHEMA_METHOD_ORDER = (c.GET, c.CREATE, c.UPDATE, c.FILTER)


def sorted_schema_methods(methods: typing.Iterable[str]) -> typing.List[str]:
    known_methods = list(methods)
    known = [m for m in SCHEMA_METHOD_ORDER if m in known_methods]
    return known + [m for m in known_methods if m not in SCHEMA_METHOD_ORDER]


def resource_parameter_name(resource_name: str, prop_name: str) -> str:
    """Key under which a resource's id parameter lives in components/parameters."""
    return resource_name + prop_name.capitalize()


def resource_field_parameter_name(resource_name: str, prop_name: str) -> str:
    """Key under which a resource's field parameter lives.

    Deliberately not the id parameter's key: two models can share a class
    name (`Resource` is both an element resource and an agent one), and one
    of them holding as a plain field what the other holds as its id would
    otherwise overwrite the id parameter -- leaving the `{ResourceUuid}` of
    the path with nothing declaring it.
    """
    return "{}_{}".format(resource_name, prop_name)


def schema_body_key(body: typing.Any) -> str:
    """Stable comparison key for a schema body."""
    return json.dumps(body, sort_keys=True, default=str)


# The filter language collapses to one string parameter, which is the cost
# of having it: a generated client gets `q *string` and can neither type
# nor check what goes in. The grammar rides in the description, and the
# fields it may name are listed in an extension so a generator that wants
# to do better has something to read.
FILTER_LANG_DESCRIPTION = """\
Filter expression (a subset of AIP-160). Combines with the field
parameters, which stay the typed way to ask for equality.

    name = "vm1" AND size > 10
    tags:"env:prod" OR tags:"env:staging"
    NOT (state = error) AND created_at >= "2026-07-01T00:00:00Z"

Operators: `=` `!=` `<` `<=` `>` `>=`, `:` (an array holds the element,
or with `*` that the field is set), `AND` `OR` `NOT`, parentheses.
The keywords are uppercase, and `OR` binds tighter than `AND`. Values
carrying `:`, `.` or spaces must be quoted."""


def filter_lang_parameter(name, field_names=()):
    """The query parameter that carries a filter expression."""
    parameter = {
        "name": name,
        "in": "query",
        "required": False,
        "description": FILTER_LANG_DESCRIPTION,
        "schema": {"type": "string"},
        "example": 'name = "vm1"',
    }
    if field_names:
        parameter["x-ra-filter-fields"] = sorted(field_names)
    return parameter


class ResourceSchemaGenerator:
    def __init__(self, resource, route, openapi_version):
        super().__init__()
        self._resource = resource
        self._route = route
        self._openapi_version = openapi_version

    @property
    def resource_name(self):
        return self._resource.get_model().__name__

    def resource_method_name(self, method):
        return f"{self.resource_name}_{method.capitalize()}"

    def resource_prop_name(self, prop_name):
        return resource_parameter_name(self.resource_name, prop_name)

    def resource_field_prop_name(self, prop_name):
        return resource_field_parameter_name(self.resource_name, prop_name)

    def get_prop_kwargs(self, name):
        try:
            kwargs = dict(
                self._resource.get_model().properties.properties[name].get_kwargs()
            )
        except KeyError:
            kwargs = {}
        kwargs["openapi"] = self._openapi_version
        return kwargs

    def generate_parameter_object(self, request):
        parameters = {}
        has_id_property = False
        for name, prop in self._resource.get_fields_by_request(request):
            prop_kwargs = self.get_prop_kwargs(name)
            schema = prop.get_type().to_openapi_spec(prop_kwargs)
            try:
                is_id = prop.is_id_property()
            except KeyError:
                is_id = False
            # components/parameters is one flat namespace for the whole
            # document, so the key has to name the resource too: plain
            # "name" or "status" means something different on every model.
            parameters[self.resource_field_prop_name(prop.api_name)] = {
                "name": prop.api_name,
                "in": "query",
                "schema": schema,
            }
            if is_id:
                has_id_property = True
                # A collection can be filtered by the id as well as by any
                # other field, so the field parameter above stands; this is
                # the path one, and its key must match the {ModelId}
                # placeholder the route builds.
                component_name = self.resource_prop_name(name)
                parameters[component_name] = {
                    "name": component_name,
                    "in": "path",
                    "schema": schema,
                    "required": True,
                }
        if not has_id_property:
            try:
                model = self._resource.get_model()
                id_prop_struct = model.get_id_property()
                id_prop = next(iter(id_prop_struct.items()))
                name, prop = id_prop
                prop = prop(value=prop._kwargs.get("default", 0))
                prop_kwargs = self.get_prop_kwargs(name)
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
        return self._resource.generate_schema_object(method, self._openapi_version)


class Schema:
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
