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

from restalchemy.dm import relationships
from restalchemy.storage.sql import orm
from restalchemy.tests.functional.restapi.ra_based.microservice import models


class VM(models.VM, orm.SQLStorableMixin):
    __tablename__ = "vms"


class VMNoProcessFilters(models.VM, orm.SQLStorableMixin):
    __tablename__ = "vms"


class VMNoSort(models.VM, orm.SQLStorableMixin):
    __tablename__ = "vms"


class VMDefSort(models.VM, orm.SQLStorableMixin):
    __tablename__ = "vms"


class Port(models.Port, orm.SQLStorableMixin):
    __tablename__ = "ports"

    vm = relationships.relationship(VM, required=True)


class IpAddress(models.IpAddress, orm.SQLStorableMixin):
    __tablename__ = "ip_addresses"

    port = relationships.relationship(Port, required=True)


class Tag(models.Tag, orm.SQLStorableMixin):
    __tablename__ = "tags"

    vm = relationships.relationship(VM, required=True)
