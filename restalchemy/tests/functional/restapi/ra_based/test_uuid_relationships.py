# Copyright 2026 Genesis Corporation
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

"""`uuid_relationships` over HTTP, against a real database.

A relationship is written as the URI of the related resource. The option
lets the named ones be written as a bare UUID as well, which is the whole
of what these drive: a body, a field parameter and a URI all reaching the
same row, and the answers a caller gets when the UUID names nothing, is
not a UUID at all, or belongs to a resource that a UUID alone cannot
address.
"""

import contextlib
import socket
import uuid

import requests

from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.api import routes
from restalchemy.dm import filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.storage.sql import orm
from restalchemy.tests.functional import base
from restalchemy.tests.functional.restapi.ra_based.microservice import service

MIGRATION = "test-uuid-relationships-migration-561a42"

VM1 = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
VM2 = uuid.UUID("00000000-0000-0000-0000-0000000000a2")
PORT1 = uuid.UUID("00000000-0000-0000-0000-0000000000b1")
UNKNOWN = uuid.UUID("00000000-0000-0000-0000-0000000000ff")


class UuidRelVM(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "test_uuid_rel_vms"

    name = properties.property(types.String(max_length=255), default="")


class UuidRelPort(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "test_uuid_rel_ports"

    vm = relationships.relationship(UuidRelVM, required=True)
    mac = properties.property(types.Mac(), default="00:00:00:00:00:00")


class BaseRule(models.ModelWithUUID):
    """The fields both rule models below carry.

    Two models over one table, because the point of comparison is the
    resource: one lists its relationships in `uuid_relationships` and the
    other does not, and a model maps to a single resource.
    """

    vm = relationships.relationship(UuidRelVM, required=True)
    port = relationships.relationship(UuidRelPort, required=True)
    name = properties.property(types.String(max_length=255), default="")


class UuidRelRule(BaseRule, orm.SQLStorableMixin):
    __tablename__ = "test_uuid_rel_rules"


class StrictRule(BaseRule, orm.SQLStorableMixin):
    __tablename__ = "test_uuid_rel_rules"


class UuidRelVMController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        UuidRelVM,
        convert_underscore=False,
    )


class UuidRelPortController(controllers.BaseNestedResourceController):
    __pr_name__ = "vm"
    __resource__ = resources.ResourceByRAModel(
        UuidRelPort,
        convert_underscore=False,
    )


class UuidRelRuleController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        UuidRelRule,
        convert_underscore=False,
        process_filters=True,
        uuid_relationships=["vm", "port"],
    )


class StrictRuleController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        StrictRule,
        convert_underscore=False,
        process_filters=True,
    )


class UuidRelPortRoute(routes.Route):
    __controller__ = UuidRelPortController
    __allow_methods__ = [routes.CREATE, routes.FILTER, routes.GET]


class UuidRelVMRoute(routes.Route):
    __controller__ = UuidRelVMController
    __allow_methods__ = [routes.CREATE, routes.FILTER, routes.GET]

    ports = routes.route(UuidRelPortRoute, resource_route=True)


class UuidRelRuleRoute(routes.Route):
    __controller__ = UuidRelRuleController
    __allow_methods__ = [routes.CREATE, routes.FILTER, routes.GET, routes.UPDATE]


class StrictRuleRoute(routes.Route):
    __controller__ = StrictRuleController
    __allow_methods__ = [routes.CREATE, routes.FILTER, routes.GET]


class Root(routes.RootRoute):
    vms = routes.route(UuidRelVMRoute)
    rules = routes.route(UuidRelRuleRoute)
    strictrules = routes.route(StrictRuleRoute)


class UuidRelationshipsTestCase(base.BaseWithDbMigrationsTestCase):
    __LAST_MIGRATION__ = MIGRATION
    __FIRST_MIGRATION__ = MIGRATION

    def setUp(self):
        super(UuidRelationshipsTestCase, self).setUp()

        self._vm1 = UuidRelVM(uuid=VM1, name="vm1")
        self._vm1.save()
        self._vm2 = UuidRelVM(uuid=VM2, name="vm2")
        self._vm2.save()
        self._port = UuidRelPort(uuid=PORT1, vm=self._vm1, mac="00:00:00:00:00:01")
        self._port.save()

        self._port_num = self._find_free_port()
        self._service = service.RESTService(
            bind_host="127.0.0.1",
            bind_port=self._port_num,
            app_root=service.build_wsgi_application(app_root=Root),
        )
        self._service.start()
        self.addCleanup(self._service.stop)

    @staticmethod
    def _find_free_port():
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("127.0.0.1", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def _url(self, path):
        return "http://127.0.0.1:%s%s" % (self._port_num, path)

    @staticmethod
    def _vm_uri(vm):
        return "/vms/%s" % vm.uuid

    @staticmethod
    def _port_uri(port):
        return "/vms/%s/ports/%s" % (port.vm.uuid, port.uuid)

    def _post_rule(self, collection="rules", **body):
        body.setdefault("vm", str(VM1))
        body.setdefault("port", self._port_uri(self._port))
        return requests.post(self._url("/%s/" % collection), json=body)

    def _stored_rule(self, rule_uuid):
        return UuidRelRule.objects.get_one(
            filters={"uuid": filters.EQ(uuid.UUID(rule_uuid))},
        )

    def test_a_bare_uuid_names_the_related_resource(self):
        response = self._post_rule(name="rule1")

        self.assertEqual(201, response.status_code, response.text)
        body = response.json()
        self.assertEqual(
            {
                "uuid": body["uuid"],
                "vm": self._vm_uri(self._vm1),
                "port": self._port_uri(self._port),
                "name": "rule1",
            },
            body,
        )
        self.assertEqual(
            self._url("/rules/%s" % body["uuid"]),
            response.headers["location"],
        )
        self.assertEqual(VM1, self._stored_rule(body["uuid"]).vm.uuid)

    def test_a_uri_is_still_accepted(self):
        response = self._post_rule(vm=self._vm_uri(self._vm2), name="rule2")

        self.assertEqual(201, response.status_code, response.text)
        body = response.json()
        self.assertEqual(self._vm_uri(self._vm2), body["vm"])
        self.assertEqual(VM2, self._stored_rule(body["uuid"]).vm.uuid)

    def test_the_field_is_still_read_back_as_a_uri(self):
        rule_uuid = self._post_rule(name="rule3").json()["uuid"]

        response = requests.get(self._url("/rules/%s" % rule_uuid))

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(self._vm_uri(self._vm1), response.json()["vm"])

    def test_a_bare_uuid_is_accepted_on_update(self):
        rule_uuid = self._post_rule(name="rule4").json()["uuid"]

        response = requests.put(
            self._url("/rules/%s" % rule_uuid),
            json={"vm": str(VM2)},
        )

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(self._vm_uri(self._vm2), response.json()["vm"])
        self.assertEqual(VM2, self._stored_rule(rule_uuid).vm.uuid)

    def test_a_bare_uuid_filters_the_collection(self):
        mine = self._post_rule(name="mine").json()["uuid"]
        self._post_rule(vm=str(VM2), name="theirs")

        response = requests.get(self._url("/rules/?vm=%s" % VM1))

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual([mine], [rule["uuid"] for rule in response.json()])

    def test_a_bare_uuid_does_not_locate_a_nested_resource(self):
        # A port is served under its VM, so a UUID on its own does not say
        # which VM to look under.
        response = self._post_rule(port=str(PORT1))

        self.assertEqual(500, response.status_code, response.text)
        self.assertEqual("BareUuidForNestedResource", response.json()["type"])

    def test_a_uuid_naming_nothing_is_not_found(self):
        response = self._post_rule(vm=str(UNKNOWN))

        self.assertEqual(404, response.status_code, response.text)
        self.assertEqual("RecordNotFound", response.json()["type"])

    def test_a_value_that_is_no_uuid_is_rejected(self):
        response = self._post_rule(vm="not-a-uuid")

        self.assertEqual(400, response.status_code, response.text)
        self.assertEqual("ParseError", response.json()["type"])

    def test_a_resource_without_the_option_reads_uris_only(self):
        by_uri = self._post_rule(
            collection="strictrules",
            vm=self._vm_uri(self._vm1),
        )
        by_uuid = self._post_rule(collection="strictrules", vm=str(VM1))

        self.assertEqual(201, by_uri.status_code, by_uri.text)
        self.assertEqual(404, by_uuid.status_code, by_uuid.text)
        self.assertEqual("LocatorNotFound", by_uuid.json()["type"])
