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

from restalchemy.api import actions
from restalchemy.api import constants
from restalchemy.api import controllers
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.openapi import constants as oa_c
from restalchemy.openapi import utils
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    storable_models as models)


class IpAddressController(controllers.BaseNestedResourceController):
    """Port controller

    Handle POST .../v1/vms/<vm_uuid>/ports/<port_uuid>/ip_addresses/
    Handle GET .../v1/vms/<vm_uuid>/ports/<port_uuid>/ip_addresses/
    Handle GET .../v1/vms/<vm_uuid>/ports/<port_uuid>/ip_addresses/<ip_uuid>
    Handle DELETE .../vms/<vm_uuid>/ports/<port_uuid>/ip_addresses/<ip_uuid>
    """

    __resource__ = resources.ResourceByRAModel(models.IpAddress)
    __pr_name__ = "port"


class PortController(controllers.BaseNestedResourceController):
    """Port controller

    Handle POST http://127.0.0.1:8000/v1/vms/<vm_uuid>/ports/
    Handle GET http://127.0.0.1:8000/v1/vms/<vm_uuid>/ports/
    Handle GET http://127.0.0.1:8000/v1/vms/<vm_uuid>/ports/<port_uuid>
    Handle DELETE http://127.0.0.1:8000/v1/vms/<vm_uuid>/ports/<port_uuid>
    """

    __resource__ = resources.ResourceByModelWithCustomProps(
        models.Port,
        hidden_fields=resources.HiddenFieldMap(
            create=['never_call', 'some_field1'],
            filter=['never_call', 'some_field2'],
            get=['never_call', 'some_field3'],
            update=['never_call', 'some_field4'],
        )
    )
    __pr_name__ = "vm"


class PortControllerNone(PortController):

    def get_packer(self, content_type, resource_type=None):
        if content_type == constants.CONTENT_TYPE_APPLICATION_JSON:
            rt = resource_type or self.get_resource()
            return packers.JSONPackerIncludeNullFields(rt, request=self._req)
        return super(PortControllerNone,
                     self).get_packer(content_type, resource_type)


class VMController(controllers.BaseResourceController):
    """VM controller

    Handle POST http://127.0.0.1:8000/v1/vms/
    Handle GET http://127.0.0.1:8000/v1/vms/
    Handle GET http://127.0.0.1:8000/v1/vms/<uuid>
    Handle PUT http://127.0.0.1:8000/v1/vms/<uuid>
    Handle DELETE http://127.0.0.1:8000/v1/vms/<uuid>
    Handle GET http://127.0.0.1:8000/v1/vms/<uuid>/actions/poweron/invoke
    Handle GET http://127.0.0.1:8000/v1/vms/<uuid>/actions/poweroff/invoke
    """

    __resource__ = resources.ResourceByRAModel(models.VM, process_filters=True)

    def create(self, **kwargs):
        """Create VM resource

        API endpoint to create VM resource.

        """
        return super(VMController, self).create(**kwargs)

    @utils.extend_schema(summary="Power on virtual machine",
                         parameters=[oa_c.build_openapi_parameter("VMUuid")],
                         responses=oa_c.build_openapi_get_update_response(
                             "{}_{}".format(models.VM.__name__,
                                            constants.CREATE.capitalize())),
                         tags=["VM"],
                         )
    @actions.post
    def poweron(self, resource):
        resource.state = "on"
        resource.save()
        return resource

    @utils.extend_schema(summary="Power off virtual machine",
                         parameters=[oa_c.build_openapi_parameter("VMUuid")],
                         responses=oa_c.build_openapi_get_update_response(
                             "{}_{}".format(models.VM.__name__,
                                            constants.CREATE.capitalize())),
                         tags=["VM"],
                         )
    @actions.post
    def poweroff(self, resource):
        resource.state = "off"
        resource.save()
        return resource


class V1Controller(controllers.Controller):

    def filter(self, filters):
        return ["vms"]
