# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

from wsgiref.simple_server import make_server

from restalchemy.api import applications
from restalchemy.api import controllers
from restalchemy.api import middlewares
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types

HOST = "0.0.0.0"
PORT = 8000


# Storage for foo objects
foo_storage = {}
# Storage for bar objects
bar_storage = {}


# -----------------------------------------------------------------------------
# Models section
# -----------------------------------------------------------------------------
# BarModel 1--->n FooModel


class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)


# -----------------------------------------------------------------------------
# Controllers section
# -----------------------------------------------------------------------------


class V1Controller(controllers.Controller):
    """Handle http://127.0.0.1:8000/."""

    def filter(self, **kwargs):
        return ["foos", "bars"]


class FooController(controllers.Controller):
    """Handle http://127.0.0.1:8000/foos/."""

    __resource__ = resources.ResourceByRAModel(FooModel, process_filters=True)

    def create(self, foo_field1, foo_field2):
        foo = self.model(foo_field1=foo_field1, foo_field2=foo_field2)
        foo_storage[str(foo.get_id())] = foo
        return foo

    def get(self, uuid):
        return foo_storage[uuid]

    def filter(self, filters, order_by=None):
        return foo_storage.values()


bar_resource = resources.ResourceByRAModel(BarModel, process_filters=True)


class BarController1(controllers.Controller):
    """Handle http://127.0.0.1:8000/foo/<uuid>/bars/."""

    __resource__ = bar_resource

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.uuid)] = bar
        return bar


class BarController2(controllers.Controller):
    """Handle http://127.0.0.1:8000/bars/<uuid>."""

    __resource__ = bar_resource

    def get(self, uuid):
        return bar_storage[uuid]

    def delete(self, uuid):
        del bar_storage[uuid]


# -----------------------------------------------------------------------------
# Routes section
# -----------------------------------------------------------------------------


class BarRoute1(routes.Route):
    __controller__ = BarController1
    __allow_methods__ = [routes.CREATE]


class BarRoute2(routes.Route):
    __controller__ = BarController2
    __allow_methods__ = [routes.GET, routes.DELETE]


class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.FILTER, routes.CREATE, routes.GET]

    bars = routes.route(BarRoute1, resource_route=True)


class V1Route(routes.Route):
    """Router for / path."""

    __controller__ = V1Controller
    __allow_methods__ = [routes.FILTER]

    # V1Route include two nested routes
    # The first route for /foo/ path
    foos = routes.route(FooRoute)
    bars = routes.route(BarRoute2)


class UserApiApp(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


# Route to /v1/ endpoint.
setattr(
    UserApiApp,
    "v1",
    routes.route(V1Route),
)


def get_user_api_application():
    return UserApiApp


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.WSGIApp(get_user_api_application()),
        [],
    )


def main():
    # Create python WSGI server on any interface with 8000 port
    server = make_server(HOST, PORT, build_wsgi_application())

    try:
        print("Serve forever on %s:%s" % (HOST, PORT))
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()
