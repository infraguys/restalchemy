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

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types


class VM(models.ModelWithUUID):

    state = properties.property(types.String(max_length=10), required=True,
                                default="off")
    name = properties.property(types.String(max_length=255), required=True)
    just_none = properties.property(types.AllowNone(types.String),
                                    required=False, default=None)


class Port(models.CustomPropertiesMixin, models.ModelWithUUID):

    __custom_properties__ = {
        "never_call": types.String(),
        "_hidden_field": types.String(),
        "some_field1": types.String(),
        "some_field2": types.String(),
        "some_field3": types.String(),
        "some_field4": types.String(),
    }

    mac = properties.property(types.Mac(), default='00:00:00:00:00:00')
    vm = relationships.relationship(VM, required=True)

    @property
    def never_call(self):
        raise NotImplementedError('Should be call never')

    @property
    def _hidden_field(self):
        return "_hidden_field"

    @property
    def some_field1(self):
        return "some_field1"

    @property
    def some_field2(self):
        return "some_field2"

    @property
    def some_field3(self):
        return "some_field3"

    @property
    def some_field4(self):
        return "some_field4"


class IpAddress(models.ModelWithUUID):

    ip = properties.property(types.String(), default='192.168.0.1')
    port = relationships.relationship(Port, required=True)
