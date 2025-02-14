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

from restalchemy.openapi import constants
from restalchemy.openapi import structures


class OpenApi303(object):
    """OpenAPI Specification

    The OpenAPI Specification (OAS) defines a standard, language-agnostic
    interface to RESTful APIs which allows both humans and computers to
    discover and understand the capabilities of the service without access to
    source code, documentation, or through network traffic inspection. When
    properly defined, a consumer can understand and interact with the remote
    service with a minimal amount of implementation logic.

    An OpenAPI definition can then be used by documentation generation tools
    to display the API, code generation tools to generate servers and clients
    in various programming languages, testing tools, and many other use cases.

    :param info: REQUIRED. Provides metadata about the API. The metadata MAY
        be used by tooling as required.
    :type info: :class:`OpenApiInfo`
    :param paths: The available paths and operations for the API.
    :type paths: :class:`OpenApiPaths`
    :param servers: An array of Server Objects, which provide connectivity
        information to a target server. If the servers property is not
        provided, or is an empty array, the default value would be a Server
        Object with a url value of /.
    :param components: An element to hold various schemas for the
        specification.
    :type components: :class:`OpenApiComponents`
    :param security: A declaration of which security mechanisms can be used
        across the API. The list of values includes alternative security
        requirement objects that can be used. Only one of the security
        requirement objects need to be satisfied to authorize a request.
        Individual operations can override this definition. To make security
        optional, an empty security requirement ({}) can be included in the
        array.
    :param tags: A list of tags used by the specification with additional
        metadata. The order of the tags can be used to reflect on their order
        by the parsing tools. Not all tags that are used by the Operation
        Object must be declared. The tags that are not declared MAY be
        organized randomly or based on the tools' logic. Each tag name in the
        list MUST be unique.
    :param external_docs: Additional external documentation.
    """

    def __init__(
        self,
        info,
        paths=None,
        servers=None,
        components=None,
        security=None,
        tags=None,
        external_docs=None,
    ):
        super(OpenApi303, self).__init__()
        self._info = info or structures.OpenApiInfo()
        self._paths = paths or structures.OpenApiPaths()
        self._servers = servers or structures.OpenApiServers()
        self._components = components or structures.OpenApiComponents()
        self._security = security
        self._tags = tags or structures.OpenApiTags([])
        self._external_docs = external_docs

    def build_openapi_specification(self, request):
        specification = {
            "openapi": constants.OPENAPI_SPECIFICATION_3_0_3,
        }

        specification.update(self._info.build(request))
        components = self._components.build(request)
        specification.update(components)
        specification.update(self._paths.build(request, components))
        specification.update(self._servers.build(request))
        specification.update(self._tags.build(request))
        return specification
