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

    state = properties.property(
        types.String(max_length=10), required=True, default="off"
    )
    name = properties.property(
        types.String(max_length=255), required=True, example="testname"
    )
    just_none = properties.property(
        types.AllowNone(types.String()), required=False, default=None
    )
    status = properties.property(
        types.Enum(["active", "disabled"]), default="active", required=True
    )
    created = properties.property(
        types.UTCDateTimeZ(),
        default=lambda: types.DEFAULT_DATE_Z,
    )
    updated = properties.property(
        types.UTCDateTime(),
        default=lambda: types.DEFAULT_DATE,
    )


class Port(models.CustomPropertiesMixin, models.ModelWithUUID):

    __custom_properties__ = {
        "never_call": types.String(),
        "_hidden_field": types.String(),
        "some_field1": types.String(),
        "some_field2": types.String(),
        "some_field3": types.String(),
        "some_field4": types.String(),
        "some_field5": types.AllowNone(types.String()),
        "unique_field": types.String(),
    }

    mac = properties.property(types.Mac(), default="00:00:00:00:00:00")
    vm = relationships.relationship(VM, required=True)

    @property
    def never_call(self):
        raise NotImplementedError("Should be call never")

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

    @property
    def some_field5(self):
        return None

    @property
    def unique_field(self):
        return str(self.uuid)


class IpAddress(models.ModelWithUUID):

    ip = properties.property(types.String(), default="192.168.0.1")
    port = relationships.relationship(Port, required=True)


class Tag(models.ModelWithUUID):

    name = properties.property(types.String(), id_property=True, required=True)
    visible = properties.property(types.Boolean(), default=True, required=True)

    @classmethod
    def get_id_property(cls):
        return {"name": cls.id_properties["name"]}
