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
from restalchemy.openapi import impl303


SUPPORTED_OPENAPI_SPECIFICATIONS = {
    constants.OPENAPI_SPECIFICATION_3_0_3: impl303.OpenApi303,
}


class OpenApiEngine(object):
    """OpenAPI Specification Context

    Using this object, one can get a description of the API service in open
    api format. The number of arguments depends on the requirements for
    different versions of OpenAPI.

    :param info: REQUIRED. Provides metadata about the API. The metadata MAY
        be used by tooling as required.
    :param paths: The available paths and operations for the API.
    :param servers: An array of Server Objects, which provide connectivity
        information to a target server. If the servers property is not
        provided, or is an empty array, the default value would be a Server
        Object with a url value of /.
    :param components: An element to hold various schemas for the
        specification.
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

    def __init__(self, **kwargs):
        super(OpenApiEngine, self).__init__()
        self._openapi_specification_kwargs = kwargs

    def list_supported_openapi_versions(self):  # noqa
        """List of supported versions.

        :return: The list of versions strings
        """
        return list(SUPPORTED_OPENAPI_SPECIFICATIONS)

    def build_openapi_specification(self, version, request):
        spec = SUPPORTED_OPENAPI_SPECIFICATIONS[version](
            **self._openapi_specification_kwargs
        )

        return spec.build_openapi_specification(request)
