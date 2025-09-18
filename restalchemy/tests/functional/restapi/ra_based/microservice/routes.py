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
from restalchemy.openapi import structures
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    controllers,
)


class TagRoute(routes.Route):
    __controller__ = controllers.TagController
    __allow_methods__ = [
        routes.CREATE,
        routes.FILTER,
        routes.GET,
        routes.UPDATE,
        routes.DELETE,
    ]


class IpAddress(routes.Route):
    __controller__ = controllers.IpAddressController
    __allow_methods__ = [
        routes.CREATE,
        routes.FILTER,
        routes.GET,
        routes.DELETE,
    ]
    __tags__ = ["IpAddress_tag"]


class PortRoute(routes.Route):
    __controller__ = controllers.PortController
    __allow_methods__ = [
        routes.CREATE,
        routes.FILTER,
        routes.GET,
        routes.UPDATE,
        routes.DELETE,
    ]
    __tags__ = [
        structures.OpenApiTag(name="PortTestTag", description="port_descr")
    ]
    ip_addresses = routes.route(IpAddress, resource_route=True)


class PortRouteNone(routes.Route):
    __controller__ = controllers.PortControllerNone
    __allow_methods__ = [
        routes.CREATE,
        routes.FILTER,
        routes.GET,
        routes.UPDATE,
        routes.DELETE,
    ]

    ip_addresses = routes.route(IpAddress, resource_route=True)


class NotImplementedAction(routes.Action):
    __controller__ = controllers.NotImplementedMethodsController


class NotImplementedMethodsRoute(routes.Route):
    __controller__ = controllers.NotImplementedMethodsController
    __allow_methods__ = [
        routes.CREATE,
        routes.FILTER,
        routes.GET,
        # routes.UPDATE,  not allowed
        routes.DELETE,
    ]
    not_implemented_action = routes.action(NotImplementedAction, invoke=True)


class VMPowerStateAction(routes.Action):
    __controller__ = controllers.VMController


class VMPowerAction(routes.Action):
    __controller__ = controllers.VMController


class VMPowerOnAction(routes.Action):
    __controller__ = controllers.VMController


class VMPowerOffAction(routes.Action):
    __controller__ = controllers.VMController


class VMRoute(routes.Route):
    __controller__ = controllers.VMController
    __allow_methods__ = [
        routes.CREATE,
        routes.GET,
        routes.DELETE,
        routes.FILTER,
        routes.UPDATE,
    ]

    power = routes.action(VMPowerAction, invoke=True)
    power_state = routes.action(VMPowerStateAction, invoke=False)
    poweron = routes.action(VMPowerOnAction, invoke=True)
    poweroff = routes.action(VMPowerOffAction, invoke=True)
    none_ports = routes.route(PortRouteNone, resource_route=True)
    ports = routes.route(PortRoute, resource_route=True)
    tags = routes.route(TagRoute, resource_route=True)


class VMNoProcessFiltersRoute(routes.Route):
    __controller__ = controllers.VMNoProcessFiltersController
    __allow_methods__ = [
        routes.GET,
        routes.FILTER,
    ]


class VMNoSortRoute(routes.Route):
    __controller__ = controllers.VMNoSortController
    __allow_methods__ = [
        routes.CREATE,
        routes.GET,
        routes.DELETE,
        routes.FILTER,
        routes.UPDATE,
    ]


class VMDefSortRoute(routes.Route):
    __controller__ = controllers.VMDefSortController
    __allow_methods__ = [
        routes.CREATE,
        routes.GET,
        routes.DELETE,
        routes.FILTER,
        routes.UPDATE,
    ]


class V1Route(routes.Route):
    __controller__ = controllers.V1Controller
    __allow_methods__ = [routes.FILTER]

    vms = routes.route(VMRoute)
    vmsnoproccessfilters = routes.route(VMNoProcessFiltersRoute)
    vmsnosort = routes.route(VMNoSortRoute)
    vmsdefsort = routes.route(VMDefSortRoute)
    notimplementedmethods = routes.route(NotImplementedMethodsRoute)


class Root(routes.RootRoute):

    v1 = routes.route(V1Route)
