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
from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.tests.functional.restapi.sa_based.microservice import models


class VMController(controllers.Controller):
    """VM controller

    Handle POST http://127.0.0.1:8000/v1/vms/
    Handle GET http://127.0.0.1:8000/v1/vms/
    Handle GET http://127.0.0.1:8000/v1/vms/<uuid>
    Handle PUT http://127.0.0.1:8000/v1/vms/<uuid>
    Handle DELETE http://127.0.0.1:8000/v1/vms/<uuid>
    Handle GET http://127.0.0.1:8000/v1/vms/<uuid>/actions/poweron/invoke
    Handle GET http://127.0.0.1:8000/v1/vms/<uuid>/actions/poweroff/invoke
    """

    __resource__ = resources.ResourceBySAModel(models.VM)

    def _get_session(self):
        ctx = self.get_context()
        return ctx.session

    def create(self, name):
        session = self._get_session()
        vm = self.model(name=name)
        session.add(vm)
        session.commit()
        return vm

    def get(self, uuid):
        session = self._get_session()
        vm = session.query(self.model).filter(self.model.uuid == uuid).one()
        return vm

    def delete(self, uuid):
        session = self._get_session()
        session.query(self.model).filter(self.model.uuid == uuid).delete()
        session.commit()

    def update(self, uuid, name, **kwargs):
        session = self._get_session()
        vm = session.query(self.model).filter(self.model.uuid == uuid).one()
        vm.name = name
        session.commit()
        return vm

    def filter(self, filters):
        session = self._get_session()
        vms = session.query(self.model).all()
        return vms

    @actions.post
    def poweron(self, resource):
        session = self._get_session()
        resource.state = "on"
        session.commit()
        return resource

    @actions.post
    def poweroff(self, resource):
        session = self._get_session()
        resource.state = "off"
        session.commit()
        return resource


class V1Controller(controllers.Controller):

    def filter(self, filters):
        return ["vms"]


class RootController(controllers.Controller):

    def filter(self, filters):
        return ["v1"]
