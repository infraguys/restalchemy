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

import random
import uuid as pyuuid

import mock
import requests
from six.moves.urllib import parse

from restalchemy.common import utils
from restalchemy.storage import exceptions
from restalchemy.storage.sql import engines
from restalchemy.tests.functional import consts
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    storable_models as models)
from restalchemy.tests.functional.restapi.ra_based.microservice import service
from restalchemy.tests.unit import base


TEMPL_SERVICE_ENDPOINT = utils.lastslash("http://127.0.0.1:%s/")
TEMPL_ROOT_COLLECTION_ENDPOINT = TEMPL_SERVICE_ENDPOINT
TEMPL_V1_COLLECTION_ENDPOINT = utils.lastslash(parse.urljoin(
    TEMPL_SERVICE_ENDPOINT, 'v1'))
TEMPL_VMS_COLLECTION_ENDPOINT = utils.lastslash(parse.urljoin(
    TEMPL_V1_COLLECTION_ENDPOINT, 'vms'))
TEMPL_VM_RESOURCE_ENDPOINT = parse.urljoin(TEMPL_VMS_COLLECTION_ENDPOINT, '%s')
TEMPL_POWERON_ACTION_ENDPOINT = parse.urljoin(
    utils.lastslash(TEMPL_VM_RESOURCE_ENDPOINT),
    'actions/poweron/invoke')
TEMPL_PORTS_COLLECTION_ENDPOINT = utils.lastslash(parse.urljoin(
    utils.lastslash(TEMPL_VM_RESOURCE_ENDPOINT), 'ports'))
TEMPL_PORT_RESOURCE_ENDPOINT = parse.urljoin(TEMPL_PORTS_COLLECTION_ENDPOINT,
                                             '%s')


class BaseResourceTestCase(base.BaseTestCase):

    def get_endpoint(self, template, *args):
        return template % ((self.service_port,) + tuple(args))

    def setUp(self):
        super(BaseResourceTestCase, self).setUp()
        engines.engine_factory.configure_factory(consts.DATABASE_URI)
        engine = engines.engine_factory.get_engine()
        self.session = engine.get_session()
        self.session.execute("""CREATE TABLE IF NOT EXISTS vms (
            uuid CHAR(36) NOT NULL,
            state VARCHAR(10) NOT NULL,
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (uuid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8;""", None)
        self.service_port = random.choice(range(2100, 2200))
        url = parse.urlparse(self.get_endpoint(TEMPL_SERVICE_ENDPOINT))
        self._service = service.RESTService(bind_host=url.hostname,
                                            bind_port=url.port)
        self._service.start()

    def tearDown(self):
        super(BaseResourceTestCase, self).tearDown()
        self._service.stop()
        self.session.execute("DROP TABLE IF EXISTS vms;", None)


class TestRootResourceTestCase(BaseResourceTestCase):

    def test_get_versions_list(self):

        response = requests.get(self.get_endpoint(
            TEMPL_ROOT_COLLECTION_ENDPOINT))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["v1"])


class TestVersionsResourceTestCase(BaseResourceTestCase):

    def test_get_resources_list(self):

        response = requests.get(
            self.get_endpoint(TEMPL_V1_COLLECTION_ENDPOINT))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["vms"])


class TestVMResourceTestCase(BaseResourceTestCase):

    def _insert_vm_to_db(self, uuid, name, state):
        vm = models.VM(uuid=uuid, name=name, state=state)
        vm.save()

    def _vm_exists_in_db(self, uuid):
        try:
            models.VM.objects.get_one(filters={'uuid': uuid})
            return True
        except exceptions.RecordNotFound:
            return False

    @mock.patch('uuid.uuid4')
    def test_create_vm_resource_successful(self, uuid4_mock):
        RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        uuid4_mock.return_value = RESOURCE_ID
        vm_request_body = {
            "name": "test"
        }
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "test",
            "state": "off"
        }
        LOCATION = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT, RESOURCE_ID)

        response = requests.post(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT), json=vm_request_body)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'], LOCATION)
        self.assertEqual(response.json(), vm_response_body)

    def test_get_vm_resource_by_uuid_successful(self):
        RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="test", state="off")
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "test",
            "state": "off"
        }
        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)

        response = requests.get(VM_RES_ENDPOINT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_update_vm_resource_successful(self):
        RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="old", state="off")
        vm_request_body = {
            "name": "new"
        }
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "new",
            "state": "off"
        }
        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)

        response = requests.put(VM_RES_ENDPOINT, json=vm_request_body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_delete_vm_resource_successful(self):
        RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="test", state="off")

        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)

        response = requests.delete(VM_RES_ENDPOINT)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(self._vm_exists_in_db(RESOURCE_ID))

    def test_process_vm_action_successful(self):
        RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="test", state="off")
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "test",
            "state": "on"
        }
        POWERON_ACT_ENDPOINT = self.get_endpoint(TEMPL_POWERON_ACTION_ENDPOINT,
                                                 RESOURCE_ID)

        response = requests.post(POWERON_ACT_ENDPOINT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_get_collection_vms_successful(self):
        RESOURCE_ID1 = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        RESOURCE_ID2 = pyuuid.UUID("00000000-0000-0000-0000-000000000002")
        self._insert_vm_to_db(uuid=RESOURCE_ID1, name="test1", state="off")
        self._insert_vm_to_db(uuid=RESOURCE_ID2, name="test2", state="on")
        vm_response_body = [{
            "uuid": str(RESOURCE_ID1),
            "name": "test1",
            "state": "off"
        }, {
            "uuid": str(RESOURCE_ID2),
            "name": "test2",
            "state": "on"
        }]

        response = requests.get(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)


class TestNestedResourceTestCase(BaseResourceTestCase):

    def setUp(self):
        super(TestNestedResourceTestCase, self).setUp()
        self.session.execute("""CREATE TABLE IF NOT EXISTS ports (
            uuid CHAR(36) NOT NULL,
            mac CHAR(17) NOT NULL,
            vm CHAR(36) NOT NULL,
            PRIMARY KEY (uuid),
            CONSTRAINT FOREIGN KEY ix_vms_uuid (vm) REFERENCES vms (uuid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8;""", None)
        self.vm1 = models.VM(
            uuid=pyuuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="vm1",
            state="on")
        self.vm1.save(session=self.session)
        self.vm2 = models.VM(
            uuid=pyuuid.UUID("00000000-0000-0000-0000-000000000002"),
            name="vm2",
            state="off")
        self.vm2.save(session=self.session)
        self.session.commit()

    def tearDown(self):
        self.session.execute("DROP TABLE IF EXISTS ports;", None)
        super(TestNestedResourceTestCase, self).tearDown()

    @mock.patch('uuid.uuid4')
    def test_create_nested_resource_successful(self, uuid4_mock):
        VM_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        PORT_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000003")
        uuid4_mock.return_value = PORT_RESOURCE_ID
        port_request_body = {
            "mac": "00:00:00:00:00:03"
        }
        port_response_body = {
            "uuid": str(PORT_RESOURCE_ID),
            "mac": "00:00:00:00:00:03",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path
        }
        LOCATION = self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT,
                                     VM_RESOURCE_ID,
                                     PORT_RESOURCE_ID)

        response = requests.post(
            self.get_endpoint(TEMPL_PORTS_COLLECTION_ENDPOINT, VM_RESOURCE_ID),
            json=port_request_body)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'], LOCATION)
        self.assertEqual(response.json(), port_response_body)

    def test_get_nested_resource_successful(self):
        VM_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        PORT_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000003")
        port = models.Port(uuid=PORT_RESOURCE_ID,
                           mac="00:00:00:00:00:03",
                           vm=self.vm1)
        port.save(session=self.session)
        self.session.commit()
        port_response_body = {
            "uuid": str(PORT_RESOURCE_ID),
            "mac": "00:00:00:00:00:03",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path
        }

        response = requests.get(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT,
                              VM_RESOURCE_ID,
                              PORT_RESOURCE_ID))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), port_response_body)

    def test_get_ports_collection_successful(self):
        VM_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        PORT1_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000003")
        PORT2_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000004")
        PORT3_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000005")
        port1 = models.Port(uuid=PORT1_RESOURCE_ID,
                            mac="00:00:00:00:00:03",
                            vm=self.vm1)
        port1.save(session=self.session)
        port2 = models.Port(uuid=PORT2_RESOURCE_ID,
                            mac="00:00:00:00:00:04",
                            vm=self.vm1)
        port2.save(session=self.session)
        port3 = models.Port(uuid=PORT3_RESOURCE_ID,
                            mac="00:00:00:00:00:05",
                            vm=self.vm2)
        port3.save(session=self.session)
        ports_response_body = [{
            "uuid": str(PORT1_RESOURCE_ID),
            "mac": "00:00:00:00:00:03",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path
        }, {
            "uuid": str(PORT2_RESOURCE_ID),
            "mac": "00:00:00:00:00:04",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path
        }]
        self.session.commit()

        response = requests.get(
            self.get_endpoint(TEMPL_PORTS_COLLECTION_ENDPOINT, VM_RESOURCE_ID))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ports_response_body)

    def test_delete_nested_resource_successful(self):
        VM_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
        PORT_RESOURCE_ID = pyuuid.UUID("00000000-0000-0000-0000-000000000003")
        port = models.Port(uuid=PORT_RESOURCE_ID,
                           mac="00:00:00:00:00:03",
                           vm=self.vm1)
        port.save(session=self.session)
        self.session.commit()

        response = requests.delete(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT,
                              VM_RESOURCE_ID,
                              PORT_RESOURCE_ID))

        self.assertEqual(response.status_code, 204)
        self.assertRaises(exceptions.RecordNotFound,
                          models.Port.objects.get_one,
                          filters={'uuid': PORT_RESOURCE_ID})
