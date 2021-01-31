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
from restalchemy.api import routes
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    controllers)


class IpAddress(routes.Route):
    __controller__ = controllers.IpAddressController
    __allow_methods__ = [routes.CREATE, routes.FILTER, routes.GET,
                         routes.DELETE]


class PortRoute(routes.Route):
    __controller__ = controllers.PortController
    __allow_methods__ = [routes.CREATE, routes.FILTER, routes.GET,
                         routes.DELETE]

    ip_addresses = routes.route(IpAddress, resource_route=True)


class VMPowerOnAction(routes.Action):
    __controller__ = controllers.VMController


class VMPowerOffAction(routes.Action):
    __controller__ = controllers.VMController


class VMRoute(routes.Route):
    __controller__ = controllers.VMController
    __allow_methods__ = [routes.CREATE, routes.GET, routes.DELETE,
                         routes.FILTER, routes.UPDATE]

    poweron = routes.action(VMPowerOnAction, invoke=True)
    poweroff = routes.action(VMPowerOffAction, invoke=True)
    ports = routes.route(PortRoute, resource_route=True)


class V1Route(routes.Route):
    __controller__ = controllers.V1Controller
    __allow_methods__ = [routes.FILTER]

    vms = routes.route(VMRoute)


class Root(routes.Route):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]

    v1 = routes.route(V1Route)
