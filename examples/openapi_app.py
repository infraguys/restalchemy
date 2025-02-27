# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2023 v.burygin
#
#    All Rights Reserved.
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

from wsgiref.simple_server import make_server

from restalchemy.api import actions
from restalchemy.api import applications
from restalchemy.api import controllers
from restalchemy.api import middlewares
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.api import constants

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types

from restalchemy.openapi import engines as openapi_engines
from restalchemy.openapi import structures as openapi_structures
from restalchemy.openapi import utils as oa_utils
from restalchemy.openapi import constants as oa_c

HOST = "0.0.0.0"
PORT = 8000


# There's an example of custom openapi spec, see File* models, controllers and
#   routes. If you don't need that - just skip them.


class FileModel(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)


# Example controller with custom openapi specs
class FilesController(controllers.Controller):
    """Controller for /v1/files/[<id>] endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=FileModel,
        process_filters=True,
        convert_underscore=False,
    )

    def create(self, **kwargs):
        # Implement file upload logic here
        pass

    # Example of custom openapi spec for file upload/download,
    #   see restalchemy.openapi.constants for other request-response templates
    create.openapi_schema = oa_utils.Schema(
        summary="Upload file",
        parameters=(),
        responses=oa_c.build_openapi_create_response(
            "%s_Create" % __resource__.get_model().__name__
        ),
        request_body=oa_c.build_openapi_req_body_multipart(
            description="Upload file to docs set",
            properties={"file": {"format": "binary", "type": "string"}},
        ),
    )

    # There's decorator too, but openapi_schema attribute usage
    #   is recommended, see below.
    @oa_utils.extend_schema(
        summary="Download file",
        parameters=(),
        responses=oa_c.build_openapi_response_octet_stream(),
    )
    @actions.get
    def download(self, resource, **kwargs):
        # Some function which returns file data
        data = resource.download_file()
        headers = {
            "Content-Type": constants.CONTENT_TYPE_OCTET_STREAM,
            "Content-Disposition": 'attachment; filename="%s"' % resource.name,
        }

        return data, 200, headers

    download.openapi_schema = oa_utils.Schema(
        summary="Download file",
        parameters=(),
        responses=oa_c.build_openapi_response_octet_stream(),
    )


class FileDownloadAction(routes.Action):
    """Handler for /v1/files/<id>/actions/download endpoint"""

    __controller__ = FilesController


class FilesRoute(routes.Route):
    """Handler for /v1/files/<id> endpoint"""

    __controller__ = FilesController
    __allow_methods__ = [
        routes.CREATE,
        routes.DELETE,
        routes.FILTER,
        routes.GET,
        routes.UPDATE,
    ]

    download = routes.action(FileDownloadAction, invoke=True)


class RootController(controllers.RoutesListController):
    """Controller for / endpoint"""

    __TARGET_PATH__ = "/"


class ApiEndpointController(controllers.RoutesListController):
    """Controller for /v1/ endpoint"""

    __TARGET_PATH__ = "/v1/"


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint"""

    __controller__ = ApiEndpointController
    __allow_methods__ = [
        routes.FILTER,
        routes.GET,
    ]

    specifications = routes.action(routes.OpenApiSpecificationRoute)
    files = routes.route(FilesRoute)


class UserApiApp(routes.RootRoute):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


# Route to /v1/ endpoint.
setattr(
    UserApiApp,
    "v1",
    routes.route(ApiEndpointRoute),
)


def get_openapi_engine():
    openapi_engine = openapi_engines.OpenApiEngine(
        info=openapi_structures.OpenApiInfo(),
        paths=openapi_structures.OpenApiPaths(),
        components=openapi_structures.OpenApiComponents(),
    )
    return openapi_engine


def get_user_api_application():
    return UserApiApp


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.OpenApiApplication(
            route_class=get_user_api_application(),
            openapi_engine=get_openapi_engine(),
        ),
        [],
    )


def main():
    """

    After start you can try curl http://127.0.0.1:8000/v1/specifications/3.0.3

    """
    server = make_server(HOST, PORT, build_wsgi_application())

    try:
        print("Serve forever on %s:%s" % (HOST, PORT))
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()
