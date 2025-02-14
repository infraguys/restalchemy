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

import collections
import posixpath

from restalchemy.api import constants as c
from restalchemy.common import utils
from restalchemy.openapi import constants as oa_c
from restalchemy.openapi import utils as oa_utils


class OpenApiContact(object):
    """Contact Object

    Contact information for the exposed API.

    :param name: The identifying name of the contact person/organization.
    :type name: str
    :param url: The URL pointing to the contact information. MUST be in the
        format of a URL.
    :type url: str
    :param email: The email address of the contact person/organization. MUST
        be in the format of an email address.
    :type email: str
    """

    def __init__(self, name=None, url=None, email=None):
        super(OpenApiContact, self).__init__()
        self._name = name
        self._url = url
        self._email = email

    def build(self, request):
        contact_spec = {
            "name": self._name,
            "url": self._url,
            "email": self._email,
        }

        return {"contact": {k: v for k, v in contact_spec.items()}}


class OpenApiLicense(object):
    """License Object

    License information for the exposed API.

    :param name: REQUIRED. The license name used for the API.
    :type name: str
    :param url: A URL to the license used for the API. MUST be in the format
        of a URL.
    :type url: str
    """

    def __init__(self, name, url=None):
        super(OpenApiLicense, self).__init__()
        self._name = name
        self._url = url

    def build(self, request):
        license_spec = {
            "name": self._name,
        }

        if self._url:
            license_spec["url"] = self._url

        return {"license": license_spec}


class OpenApiApacheLicense(OpenApiLicense):

    def __init__(self):
        super(OpenApiApacheLicense, self).__init__(
            name="Apache 2.0",
            url="https://www.apache.org/licenses/LICENSE-2.0.html",
        )


class OpenApiInfo(object):
    """Info Object

    The object provides metadata about the API. The metadata MAY be used by
    the clients if needed, and MAY be presented in editing or documentation
    generation tools for convenience.


    :param title: REQUIRED. The title of the API.
    :type title: str
    :param version: REQUIRED. The version of the OpenAPI document (which is
        distinct from the OpenAPI Specification version or the API
        implementation version).
    :type version: str
    :param description: A short description of the API. CommonMark syntax
        (https://spec.commonmark.org/) MAY be used for rich text
        representation.
    :type description: str
    :param license: The license information for the exposed API.
    :type license: :class:`OpenApiLicense`
    :param terms_of_service: A URL to the Terms of Service for the API. MUST
        be in the format of a URL.
    :type terms_of_service: str
    :param contact: The contact information for the exposed API.

    """

    def __init__(
        self,
        title=None,
        version=None,
        description=None,
        license=None,
        terms_of_service=None,
        contact=None,
    ):
        super(OpenApiInfo, self).__init__()
        self._title = title or "OpenAPI service schema"
        self._version = version or "1.0.0"
        self._description = description or ""
        self._license = license
        self._terms_of_service = terms_of_service
        self._contact = contact

    def build(self, request):
        info_spec = {
            "title": self._title,
            "version": self._version,
        }

        if self._description:
            info_spec["description"] = self._description

        if self._terms_of_service:
            info_spec["termsOfService"] = self._terms_of_service

        if self._license:
            info_spec.update(self._license.build(request))
        if self._contact:
            info_spec.update(self._contact.build(request))

        return {"info": info_spec}


class OpenApiPaths(object):

    def __init__(self):
        super(OpenApiPaths, self).__init__()

    def _build_api_paths(self, route, current_path, request, parameters=None):
        result_spec = collections.defaultdict(dict)

        # process collection paths
        for http_method, ra_method in c.HTTP_TO_RA_COLLECTION_METHODS.items():
            if route.check_allow_methods(ra_method):
                if current_path == "/":
                    result_spec[current_path][http_method.lower()] = {
                        "summary": "Base application url",
                        "responses": oa_c.OPENAPI_FILTER_RESPONSE,
                        "operationId": "Get_urls",
                    }
                else:
                    result_spec[current_path][http_method.lower()] = {}
            # process next routes
            for route_name in route.get_routes():
                next_route = route.get_route(route_name)
                if next_route.is_collection_route():
                    next_path = utils.lastslash(
                        posixpath.join(current_path, route_name)
                    )
                    result_spec.update(
                        self._build_api_paths(
                            next_route, next_path, request, parameters
                        )
                    )
                    paths, schemas = next_route(
                        request
                    ).build_openapi_specification(next_path, parameters)
                    result_spec.update(paths)

        return result_spec

    def build(self, request, parameters=None):
        paths_spec = {}

        main_route = request.application.main_route
        paths_spec.update(
            self._build_api_paths(main_route, "/", request, parameters)
        )

        return {"paths": paths_spec}


class OpenApiComponents(object):

    def __init__(self):
        super(OpenApiComponents, self).__init__()

    @staticmethod
    def _build_schemas_by_resources(route, schema_generator):
        schemas = {"schemas": {"Error": oa_c.ERROR_SCHEMA}}
        for method in route.get_allow_methods():
            if method == c.DELETE:
                continue
            schema_name = schema_generator.resource_method_name(method)
            schemas["schemas"][schema_name] = (
                schema_generator.generate_schema_object(method)
            )
        return schemas

    @staticmethod
    def _build_parameters_by_resources(schema_generator, request):
        return {
            "parameters": schema_generator.generate_parameter_object(request),
        }

    @staticmethod
    def _build_responses():
        return {"responses": {"Error": oa_c.ERROR_RESPONSE}}

    @staticmethod
    def _merge_specs(in_spec, from_spec):
        for key, value in from_spec.items():
            in_spec[key].update(value)
        return in_spec

    def _build_api_resources(self, route, request):
        resources_spec = collections.defaultdict(dict)

        self._merge_specs(resources_spec, self._build_responses())

        resource = route.get_controller(request).get_resource()
        schema_generator = oa_utils.ResourceSchemaGenerator(resource, route)
        if resource:
            resources_spec = self._merge_specs(
                in_spec=resources_spec,
                from_spec=self._build_schemas_by_resources(
                    route=route,
                    schema_generator=schema_generator,
                ),
            )
            resources_spec = self._merge_specs(
                in_spec=resources_spec,
                from_spec=self._build_parameters_by_resources(
                    schema_generator=schema_generator, request=request
                ),
            )

        for route_name in route.get_routes():
            next_route = route.get_route(route_name)(request)
            resources_spec = self._merge_specs(
                in_spec=resources_spec,
                from_spec=self._build_api_resources(next_route, request),
            )

        return resources_spec

    def build(self, request):
        main_route = request.application.main_route
        component_spec = self._build_api_resources(main_route, request)

        return {"components": component_spec}


class OpenApiSecurity(object):

    def __init__(self):
        super(OpenApiSecurity, self).__init__()


class OpenApiTag(object):
    """Tag Object

    Adds metadata to a single tag that is used by the Operation Object. It is
    not mandatory to have a Tag Object per tag defined in the Operation Object
    instances.

    :param name: REQUIRED. The name of the tag.
    :param description: A short description for the tag. CommonMark syntax MAY
        be used for rich text representation.
    :param external_docs: Additional external documentation for this tag.
    """

    def __init__(self, name, description="", external_docs=None):
        super(OpenApiTag, self).__init__()
        self._name = name
        self._description = description
        self._external_docs = external_docs

    @property
    def name(self):
        return self._name

    def build(self, request=None):
        value = {"name": self._name, "description": self._description}
        if self._external_docs:
            if isinstance(self._external_docs, OpenApiExternalDocs):
                value["externalDocs"] = self._external_docs.build(request)
        return value


class OpenApiTags(object):
    """Tags Object"""

    def __init__(self, tags):
        super(OpenApiTags, self).__init__()
        self._tags = tags

    def _build_route_tag(self, route, current_path, request):
        result_spec = list()

        # process next routes
        for route_name in route.get_routes():
            next_route = route.get_route(route_name)
            if next_route.is_collection_route():
                next_path = posixpath.join(current_path, route_name)
                result_spec.extend(
                    self._build_route_tag(next_route, next_path, request)
                )
                tags = next_route(request).openapi_tags()
                result_spec.extend(tags)
            elif next_route.is_resource_route():
                next_path = posixpath.join(current_path, route_name)
                result_spec.extend(
                    self._build_route_tag(next_route, next_path, request)
                )
                tags = next_route(request).openapi_tags()
                result_spec.extend(tags)

        return result_spec

    def build(self, request):
        tags = {"tags": []}
        for tag in self._tags:
            if isinstance(tag, OpenApiTag):
                tags["tags"].append(tag.build(request))

        main_route = request.application.main_route
        tags["tags"].extend(self._build_route_tag(main_route, "/", request))
        tags["tags"] = [
            i
            for n, i in enumerate(tags["tags"])
            if i not in tags["tags"][n + 1 :]
        ]
        return tags


class OpenApiExternalDocs(object):

    def __init__(self, url, description=None):
        super(OpenApiExternalDocs, self).__init__()
        self._url = url
        self._description = description

    def build(self, request=None):
        return {"url": self._url, "description": self._description}


class OpenApiServers(object):

    def __init__(
        self, url=None, description=None, variables=None, versions=None
    ):
        super(OpenApiServers, self).__init__()
        self._url = url
        self._description = description
        self._variables = variables
        self._versions = versions

    def build_variables(self):
        enum = self._versions or [oa_c.API_VERSION_V1]
        return self._variables or {
            "version": {"enum": enum, "default": enum[0]}
        }

    def build(self, request):
        servers = [
            {
                "url": self._url or request.host_url,
                "description": self._description or "",
                "variables": self.build_variables(),
            }
        ]
        return {"servers": servers}
