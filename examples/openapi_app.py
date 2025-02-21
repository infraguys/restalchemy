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

from restalchemy.api import applications
from restalchemy.api import controllers
from restalchemy.api import middlewares
from restalchemy.api import routes

from restalchemy.openapi import engines as openapi_engines
from restalchemy.openapi import structures as openapi_structures

HOST = "0.0.0.0"
PORT = 8000


class RootController(controllers.Controller):
    """Controller for / endpoint"""

    def filter(self, filters):
        return ["v1"]


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint"""

    __controller__ = controllers.RootController
    __allow_methods__ = [
        routes.FILTER,
        routes.GET,
    ]

    specifications = routes.action(routes.OpenApiSpecificationRoute)


class UserApiApp(routes.Route):
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
