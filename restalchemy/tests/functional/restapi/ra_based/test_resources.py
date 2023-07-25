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

import collections
import mock
import requests
from six.moves.urllib import parse
from webob import request

from functools import partial
from restalchemy.api import constants
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.common import utils
from restalchemy.dm import filters
from restalchemy.storage import exceptions
from restalchemy.storage.sql.dialect import exceptions as dialect_exc
from restalchemy.storage.sql.tables import SQLTable
from restalchemy.tests.functional import base
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    storable_models as models)
from restalchemy.tests.functional.restapi.ra_based.microservice import service

TEMPL_SERVICE_ENDPOINT = utils.lastslash("http://127.0.0.1:%s/")
TEMPL_ROOT_COLLECTION_ENDPOINT = TEMPL_SERVICE_ENDPOINT
TEMPL_SPEC_SPEC_ENDPOINT = utils.lastslash(parse.urljoin(
    TEMPL_SERVICE_ENDPOINT, 'specifications'))
TEMPL_OPENAPI_SPEC_ENDPOINT = parse.urljoin(
    TEMPL_SPEC_SPEC_ENDPOINT, '3.0.3')
TEMPL_V1_COLLECTION_ENDPOINT = utils.lastslash(parse.urljoin(
    TEMPL_SERVICE_ENDPOINT, 'v1'))
TEMPL_VMS_COLLECTION_ENDPOINT = utils.lastslash(parse.urljoin(
    TEMPL_V1_COLLECTION_ENDPOINT, 'vms'))
TEMPL_VM_RESOURCE_ENDPOINT = parse.urljoin(TEMPL_VMS_COLLECTION_ENDPOINT, '%s')
TEMPL_VMS_COLLECTION_ENDPOINT_WITH_FILTER = parse.urljoin(
    TEMPL_VMS_COLLECTION_ENDPOINT, '?%s=%s')
TEMPL_POWERON_ACTION_ENDPOINT = parse.urljoin(
    utils.lastslash(TEMPL_VM_RESOURCE_ENDPOINT),
    'actions/poweron/invoke')
TEMPL_POWEROFF_ACTION_ENDPOINT = parse.urljoin(
    utils.lastslash(TEMPL_VM_RESOURCE_ENDPOINT),
    'actions/poweroff/invoke')
TEMPL_PORTS_COLLECTION_ENDPOINT = utils.lastslash(parse.urljoin(
    utils.lastslash(TEMPL_VM_RESOURCE_ENDPOINT), 'ports'))
TEMPL_PORTSNONE_COLLECTION_ENDPOINT = utils.lastslash(parse.urljoin(
    utils.lastslash(TEMPL_VM_RESOURCE_ENDPOINT), 'none_ports'))
TEMPL_PORT_RESOURCE_ENDPOINT = parse.urljoin(TEMPL_PORTS_COLLECTION_ENDPOINT,
                                             '%s')
TEMPL_PORTNONE_RESOURCE_ENDPOINT = parse.urljoin(
    TEMPL_PORTSNONE_COLLECTION_ENDPOINT, '%s')

UUID1 = pyuuid.UUID('00000000-0000-0000-0000-000000000001')
UUID2 = pyuuid.UUID('00000000-0000-0000-0000-000000000002')
UUID3 = pyuuid.UUID('00000000-0000-0000-0000-000000000003')
UUID4 = pyuuid.UUID('00000000-0000-0000-0000-000000000004')
UUID5 = pyuuid.UUID('00000000-0000-0000-0000-000000000005')

BAD_UUID = 'bad_uuid'

DEADLOCK_EXC = dialect_exc.DeadLock(code=1213, message="fake deadlock")
DEADLOCK_RESPONSE = {
    "type": "DeadLock",
    "message": "Deadlock found when trying to get lock. Original message: "
               "fake deadlock",
    "code": 10000001,
}


class BaseResourceTestCase(base.BaseWithDbMigrationsTestCase):

    __LAST_MIGRATION__ = "e31a12-0001-rest-service-tables-migration"
    __FIRST_MIGRATION__ = "e31a12-0001-rest-service-tables-migration"

    def get_endpoint(self, template, *args):
        return template % ((self.service_port,) + tuple(args))

    def setUp(self):
        super(BaseResourceTestCase, self).setUp()

        self.service_port = random.choice(range(2000, 10000))
        url = parse.urlparse(self.get_endpoint(TEMPL_SERVICE_ENDPOINT))
        self._service = service.RESTService(bind_host=url.hostname,
                                            bind_port=url.port)
        self._service.start()

    def tearDown(self):
        super(BaseResourceTestCase, self).tearDown()

        self._service.stop()


class TestRootResourceTestCase(BaseResourceTestCase):

    def test_get_versions_list(self):

        response = requests.get(self.get_endpoint(
            TEMPL_ROOT_COLLECTION_ENDPOINT))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(response.json()),
                         ["specifications", "v1"])


class TestOpenApiSpecificationTestCase(BaseResourceTestCase):

    def test_generate_openapi_specification(self):
        info = {
            'title': 'REST API Microservice',
            'description': 'REST API Microservice for tests',
            'termsOfService': 'https://functional.tests/terms/',
            'contact': {
                'name': 'Functional Tests',
                'url': 'https://functional.tests/',
                'email': 'functional@tests.local',
            },
            'license': {
                'name': 'Apache 2.0',
                'url': 'https://www.apache.org/licenses/LICENSE-2.0.html',
            },
            'version': '1.2.3',
        }

        response = requests.get(
            self.get_endpoint(TEMPL_OPENAPI_SPEC_ENDPOINT),
        )

        self.assertEqual(200, response.status_code)

        res = response.json()

        self.assertEqual(res["openapi"], '3.0.3')
        self.assertEqual(res["info"], info)


class TestVersionsResourceTestCase(BaseResourceTestCase):

    def test_get_resources_list(self):

        response = requests.get(
            self.get_endpoint(TEMPL_V1_COLLECTION_ENDPOINT))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["vms"])


class TestVMResourceTestCase(BaseResourceTestCase):

    def tearDown(self):
        super(TestVMResourceTestCase, self).tearDown()
        packers.set_packer(constants.CONTENT_TYPE_APPLICATION_JSON,
                           packers.JSONPacker)

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
        RESOURCE_ID = UUID1
        uuid4_mock.return_value = RESOURCE_ID
        vm_request_body = {
            "name": "test"
        }
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "test",
            "state": "off",
            "status": "active"
        }
        LOCATION = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT, RESOURCE_ID)

        response = requests.post(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT), json=vm_request_body)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'], LOCATION)
        self.assertEqual(response.json(), vm_response_body)

    def test_get_vm_resource_by_uuid_successful(self):
        RESOURCE_ID = UUID1
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="test", state="off")
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "test",
            "state": "off",
            "status": "active"
        }
        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)

        response = requests.get(VM_RES_ENDPOINT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_get_vm_resource_with_null_fields_by_uuid_successful(self):
        RESOURCE_ID = UUID1
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="test", state="off")
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "test",
            "state": "off",
            "just-none": None,
            "status": "active"
        }
        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)
        packers.set_packer(constants.CONTENT_TYPE_APPLICATION_JSON,
                           packers.JSONPackerIncludeNullFields)

        response = requests.get(VM_RES_ENDPOINT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_update_vm_resource_successful(self):
        RESOURCE_ID = UUID1
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="old", state="off")
        vm_request_body = {
            "name": "new"
        }
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "new",
            "state": "off",
            "status": "active"
        }
        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)

        response = requests.put(VM_RES_ENDPOINT, json=vm_request_body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_update_vm_resource_uuid_in_body(self):
        RESOURCE_ID = UUID1
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="old", state="off")
        vm_request_body = {
            "uuid": str(UUID2),
            "name": "new"
        }

        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)

        response = requests.put(VM_RES_ENDPOINT, json=vm_request_body)

        self.assertEqual(response.status_code, 400)
        message = response.json()["message"]
        expected_message = ("Uuid (%s) in body is not equal to parsed id (%s) "
                            "from url.") % (UUID2, RESOURCE_ID)
        self.assertEqual(message, expected_message)

        vm_request_body = {
            "uuid": str(RESOURCE_ID),
            "name": "new"
        }
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "new",
            "state": "off",
            "status": "active",
        }
        response = requests.put(VM_RES_ENDPOINT, json=vm_request_body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_delete_vm_resource_successful(self):
        RESOURCE_ID = UUID1
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="test", state="off")

        VM_RES_ENDPOINT = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                            RESOURCE_ID)

        response = requests.delete(VM_RES_ENDPOINT)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(self._vm_exists_in_db(RESOURCE_ID))

    def test_process_vm_action_successful(self):
        RESOURCE_ID = UUID1
        self._insert_vm_to_db(uuid=RESOURCE_ID, name="test", state="off")
        vm_response_body = {
            "uuid": str(RESOURCE_ID),
            "name": "test",
            "state": "on",
            "status": "active"
        }
        POWERON_ACT_ENDPOINT = self.get_endpoint(TEMPL_POWERON_ACTION_ENDPOINT,
                                                 RESOURCE_ID)

        response = requests.post(POWERON_ACT_ENDPOINT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_get_collection_vms_successful(self):
        RESOURCE_ID1 = UUID1
        RESOURCE_ID2 = UUID2
        self._insert_vm_to_db(uuid=RESOURCE_ID1, name="test1", state="off")
        self._insert_vm_to_db(uuid=RESOURCE_ID2, name="test2", state="on")
        vm_response_body = [{
            "uuid": str(RESOURCE_ID1),
            "name": "test1",
            "state": "off",
            "status": "active"
        }, {
            "uuid": str(RESOURCE_ID2),
            "name": "test2",
            "state": "on",
            "status": "active"
        }]

        response = requests.get(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_get_collection_vms_with_field_definition_successful(self):
        RESOURCE_ID1 = UUID1
        RESOURCE_ID2 = UUID2
        self._insert_vm_to_db(uuid=RESOURCE_ID1, name="test1", state="off")
        self._insert_vm_to_db(uuid=RESOURCE_ID2, name="test2", state="on")
        vm_response_body = [{
            "uuid": str(RESOURCE_ID1),
        }, {
            "uuid": str(RESOURCE_ID2),
        }]

        response = requests.get(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT + "?fields=uuid"))

        self.assertEqual(200, response.status_code)
        self.assertEqual(vm_response_body, response.json())

    def test_get_collection_vms_with_fields_definition_successful(self):
        RESOURCE_ID1 = UUID1
        RESOURCE_ID2 = UUID2
        self._insert_vm_to_db(uuid=RESOURCE_ID1, name="test1", state="off")
        self._insert_vm_to_db(uuid=RESOURCE_ID2, name="test2", state="on")
        vm_response_body = [{
            "uuid": str(RESOURCE_ID1),
            "name": "test1",
        }, {
            "uuid": str(RESOURCE_ID2),
            "name": "test2",
        }]

        response = requests.get(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT + "?fields=uuid&fields=name"))

        self.assertEqual(200, response.status_code)
        self.assertEqual(vm_response_body, response.json())

    def test_get_collection_vms_with_filter_by_uuid(self):
        RESOURCE_ID1 = UUID1
        RESOURCE_ID2 = UUID2
        RESOURCE_ID3 = UUID3
        self._insert_vm_to_db(uuid=RESOURCE_ID1, name="test1", state="off")
        self._insert_vm_to_db(uuid=RESOURCE_ID2, name="test2", state="on")
        self._insert_vm_to_db(uuid=RESOURCE_ID3, name="test3", state="off")
        vm_response_body = [{
            "uuid": str(RESOURCE_ID2),
            "name": "test2",
            "state": "on",
            "status": "active"
        }]

        response = requests.get(self.get_endpoint("%s?uuid=%s" % (
            TEMPL_VMS_COLLECTION_ENDPOINT, str(RESOURCE_ID2))))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)

    def test_get_collection_vms_with_fields_definition_and_filter_by_uuid(
            self,
    ):
        RESOURCE_ID1 = UUID1
        RESOURCE_ID2 = UUID2
        RESOURCE_ID3 = UUID3
        self._insert_vm_to_db(uuid=RESOURCE_ID1, name="test1", state="off")
        self._insert_vm_to_db(uuid=RESOURCE_ID2, name="test2", state="on")
        self._insert_vm_to_db(uuid=RESOURCE_ID3, name="test3", state="off")
        vm_response_body = [{
            "uuid": str(RESOURCE_ID2),
            "state": "on"
        }]

        response = requests.get(self.get_endpoint(
            "%s?fields=uuid&uuid=%s&fields=state" % (
                TEMPL_VMS_COLLECTION_ENDPOINT, str(RESOURCE_ID2)
            )
        ))

        self.assertEqual(200, response.status_code)
        self.assertEqual(vm_response_body, response.json())

    def test_get_collection_vms_with_filter_by_two_uuid(self):
        RESOURCE_ID1 = UUID1
        RESOURCE_ID2 = UUID2
        RESOURCE_ID3 = UUID3
        self._insert_vm_to_db(uuid=RESOURCE_ID1, name="test1", state="off")
        self._insert_vm_to_db(uuid=RESOURCE_ID2, name="test2", state="on")
        self._insert_vm_to_db(uuid=RESOURCE_ID3, name="test3", state="off")
        vm_response_body = [{
            "uuid": str(RESOURCE_ID1),
            "name": "test1",
            "state": "off",
            "status": "active"
        }, {
            "uuid": str(RESOURCE_ID3),
            "name": "test3",
            "state": "off",
            "status": "active"
        }]

        response = requests.get(self.get_endpoint("%s?uuid=%s&uuid=%s" % (
            TEMPL_VMS_COLLECTION_ENDPOINT, str(RESOURCE_ID1),
            str(RESOURCE_ID3))))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), vm_response_body)


class TestNestedResourceTestCase(BaseResourceTestCase):

    __LAST_MIGRATION__ = (
        "c17a60-0002-0-rest-service-data-for-test-nested-resource"
    )

    def setUp(self):
        super(TestNestedResourceTestCase, self).setUp()

        self.vm1 = models.VM.objects.get_one(filters={
            'uuid': filters.EQ(UUID1)
        })
        self.vm2 = models.VM.objects.get_one(filters={
            'uuid': filters.EQ(UUID2)
        })

    def tearDown(self):
        super(TestNestedResourceTestCase, self).tearDown()

    @mock.patch('uuid.uuid4')
    def test_create_nested_resource_successful(self, uuid4_mock):
        VM_RESOURCE_ID = UUID1
        PORT_RESOURCE_ID = UUID3
        uuid4_mock.return_value = PORT_RESOURCE_ID
        port_request_body = {
            "mac": "00:00:00:00:00:03"
        }
        port_response_body = {
            "uuid": str(PORT_RESOURCE_ID),
            "mac": "00:00:00:00:00:03",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path,
            "some-field2": "some_field2",
            "some-field3": "some_field3",
            "some-field4": "some_field4",
        }
        LOCATION = self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT,
                                     VM_RESOURCE_ID,
                                     PORT_RESOURCE_ID)

        response = requests.post(
            self.get_endpoint(TEMPL_PORTS_COLLECTION_ENDPOINT, VM_RESOURCE_ID),
            json=port_request_body)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'], LOCATION)
        self.assertEqual(port_response_body, response.json())

    def test_update_nested_resource_successful(self):
        VM_RESOURCE_ID = UUID1
        PORT_RESOURCE_ID = UUID3
        port = models.Port(uuid=PORT_RESOURCE_ID,
                           mac="00:00:00:00:00:03",
                           vm=self.vm1)
        port.save()
        port_request_body = {
            "mac": "00:00:00:00:00:04"
        }
        port_response_body = {
            "uuid": str(PORT_RESOURCE_ID),
            "mac": "00:00:00:00:00:04",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path,
            "some-field1": "some_field1",
            "some-field2": "some_field2",
            "some-field3": "some_field3",
        }

        response = requests.put(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT,
                              VM_RESOURCE_ID,
                              PORT_RESOURCE_ID),
            json=port_request_body,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(port_response_body, response.json())

    def test_get_nested_resource_successful(self):
        VM_RESOURCE_ID = UUID1
        PORT_RESOURCE_ID = UUID3
        port = models.Port(uuid=PORT_RESOURCE_ID,
                           mac="00:00:00:00:00:03",
                           vm=self.vm1)
        port.save()
        port_response_body = {
            "uuid": str(PORT_RESOURCE_ID),
            "mac": "00:00:00:00:00:03",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path,
            "some-field1": "some_field1",
            "some-field2": "some_field2",
            "some-field4": "some_field4",
        }

        response = requests.get(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT,
                              VM_RESOURCE_ID,
                              PORT_RESOURCE_ID))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(port_response_body, response.json())

    def test_get_nested_resource_none_successful(self):
        VM_RESOURCE_ID = UUID1
        PORT_RESOURCE_ID = UUID3
        port = models.Port(uuid=PORT_RESOURCE_ID,
                           mac="00:00:00:00:00:03",
                           vm=self.vm1)
        port.save()
        port_response_body = {
            "uuid": str(PORT_RESOURCE_ID),
            "mac": "00:00:00:00:00:03",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path,
            "some-field1": "some_field1",
            "some-field2": "some_field2",
            "some-field4": "some_field4",
            "some-field5": None,
        }

        response = requests.get(
            self.get_endpoint(TEMPL_PORTNONE_RESOURCE_ENDPOINT,
                              VM_RESOURCE_ID,
                              PORT_RESOURCE_ID))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(port_response_body, response.json())

    def test_get_nested_resource_with_fields_definition_successful(self):
        VM_RESOURCE_ID = UUID1
        PORT_RESOURCE_ID = UUID3
        port = models.Port(uuid=PORT_RESOURCE_ID,
                           mac="00:00:00:00:00:03",
                           vm=self.vm1)
        port.save()
        port_response_body = {
            "uuid": str(PORT_RESOURCE_ID),
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path,
            "some-field2": "some_field2",
        }

        response = requests.get(
            self.get_endpoint(
                TEMPL_PORT_RESOURCE_ENDPOINT, VM_RESOURCE_ID, PORT_RESOURCE_ID
            ) + '?fields=uuid&fields=vm&fields=some-field2'
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(port_response_body, response.json())

    def test_get_ports_collection_successful(self):
        VM_RESOURCE_ID = UUID1
        PORT1_RESOURCE_ID = UUID3
        PORT2_RESOURCE_ID = UUID4
        PORT3_RESOURCE_ID = UUID5
        port1 = models.Port(uuid=PORT1_RESOURCE_ID,
                            mac="00:00:00:00:00:03",
                            vm=self.vm1)
        port1.save()
        port2 = models.Port(uuid=PORT2_RESOURCE_ID,
                            mac="00:00:00:00:00:04",
                            vm=self.vm1)
        port2.save()
        port3 = models.Port(uuid=PORT3_RESOURCE_ID,
                            mac="00:00:00:00:00:05",
                            vm=self.vm2)
        port3.save()
        ports_response_body = [{
            "uuid": str(PORT1_RESOURCE_ID),
            "mac": "00:00:00:00:00:03",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path,
            "some-field1": "some_field1",
            "some-field3": "some_field3",
            "some-field4": "some_field4",
        }, {
            "uuid": str(PORT2_RESOURCE_ID),
            "mac": "00:00:00:00:00:04",
            "vm": parse.urlparse(
                self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                  VM_RESOURCE_ID)).path,
            "some-field1": "some_field1",
            "some-field3": "some_field3",
            "some-field4": "some_field4",
        }]

        response = requests.get(
            self.get_endpoint(TEMPL_PORTS_COLLECTION_ENDPOINT, VM_RESOURCE_ID))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ports_response_body, response.json())

    def test_delete_nested_resource_successful(self):
        VM_RESOURCE_ID = UUID1
        PORT_RESOURCE_ID = UUID3
        port = models.Port(uuid=PORT_RESOURCE_ID,
                           mac="00:00:00:00:00:03",
                           vm=self.vm1)
        port.save()

        response = requests.delete(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT,
                              VM_RESOURCE_ID,
                              PORT_RESOURCE_ID))

        self.assertEqual(response.status_code, 204)
        self.assertRaises(exceptions.RecordNotFound,
                          models.Port.objects.get_one,
                          filters={'uuid': PORT_RESOURCE_ID})


class ResourceExceptionsTestCase(BaseResourceTestCase):

    def _insert_vm_to_db(self, uuid, name, state):
        vm = models.VM(uuid=uuid, name=name, state=state)
        vm.save()

    def test_create_parse_error_exception(self):
        vm_request_body = {
            "uuid": BAD_UUID,
            "name": "test"
        }

        response = requests.post(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT), json=vm_request_body)

        message = response.json()["message"]
        self.assertEqual(response.status_code, 400)
        expected_message = "Can't parse value: %s=%s." % ("uuid", BAD_UUID)
        self.assertEqual(message, expected_message)

    def test_filter_parse_error_exception(self):
        self._insert_vm_to_db(uuid=UUID1, name="test", state="off")

        end_point = self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT_WITH_FILTER,
            "uuid", BAD_UUID)

        response = requests.get(end_point)

        message = response.json()["message"]
        self.assertEqual(response.status_code, 400)
        expected_message = "Can't parse value: %s=%s." % ("uuid", BAD_UUID)
        self.assertEqual(message, expected_message)

    def test_resource_id_parse_error_exception(self):
        end_point = self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT,
                                      BAD_UUID)

        response = requests.get(end_point)

        message = response.json()["message"]
        self.assertEqual(response.status_code, 400)
        expected_message = "Can't parse value: %s=%s." % ("uuid", BAD_UUID)
        self.assertEqual(message, expected_message)


class TestNestedResourceForUnpackerTestCase(BaseResourceTestCase):

    __LAST_MIGRATION__ = "1a9112-0002-1-rest-service-data-for-test-unpacker"

    def test_get_resource_by_uri(self):
        uri = '/v1/vms/%s/ports/%s/ip_addresses/%s' % (
            UUID1,
            UUID2,
            UUID3,
        )
        req = request.Request.blank(uri)

        result = resources.ResourceMap.get_resource(req, uri)

        self.assertEqual(
            models.IpAddress.objects.get_one(filters={
                'uuid': filters.EQ(UUID3)
            }), result)


def raise_deadlock_exc_once(counter, original_method, obj, *args, **kwargs):
    if counter["attempt"] == 0:
        counter["attempt"] += 1
        raise DEADLOCK_EXC
    else:
        return original_method(obj, *args, **kwargs)


class TestRetryOnErrorMiddlewareBaseResourceTestCase(BaseResourceTestCase):

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.insert",
                side_effect=DEADLOCK_EXC)
    def test_create_vm_when_deadlock_raises(self, model_insert_mock):
        response = requests.post(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT), json={"name": "test"})
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_insert_mock.call_count)
        self.assertEqual(0, len(models.VM.objects.get_all()))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.insert",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.insert),
                autospec=True)
    def test_create_vm_when_deadlock_raises_once(self, model_insert_mock):
        response = requests.post(self.get_endpoint(
            TEMPL_VMS_COLLECTION_ENDPOINT), json={"name": "test"})
        self.assertEqual(201, response.status_code)
        self.assertEqual(2, model_insert_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "name": "test"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update",
                side_effect=DEADLOCK_EXC)
    def test_update_vm_when_deadlock_raises(self, model_update_mock):
        models.VM(uuid=UUID1, name="old", state="off").save()
        response = requests.put(
            self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT, UUID1),
            json={"name": "new"})
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "uuid": UUID1, "name": "old", "state": "off"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.update),
                autospec=True)
    def test_update_vm_when_deadlock_raises_once(self, model_update_mock):
        models.VM(uuid=UUID1, name="old", state="off").save()
        response = requests.put(
            self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT, UUID1),
            json={"name": "new"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "uuid": UUID1, "name": "new", "state": "off"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.delete",
                side_effect=DEADLOCK_EXC)
    def test_delete_vm_when_deadlock_raises(self, model_delete_mock):
        models.VM(uuid=UUID1, name="old", state="off").save()
        response = requests.delete(
            self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT, UUID1))
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_delete_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "uuid": UUID1, "name": "old", "state": "off"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.delete",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.delete),
                autospec=True)
    def test_delete_vm_when_deadlock_raises_once(self, model_delete_mock):
        models.VM(uuid=UUID1, name="old", state="off").save()
        response = requests.delete(
            self.get_endpoint(TEMPL_VM_RESOURCE_ENDPOINT, UUID1))
        self.assertEqual(204, response.status_code)
        self.assertEqual(2, model_delete_mock.call_count)
        self.assertEqual(0, len(models.VM.objects.get_all()))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update",
                side_effect=DEADLOCK_EXC)
    def test_vm_power_on_when_deadlock_raises(self, model_update_mock):
        models.VM(uuid=UUID1, name="old", state="off").save()
        response = requests.post(
            self.get_endpoint(TEMPL_POWERON_ACTION_ENDPOINT, UUID1))
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "uuid": UUID1, "name": "old", "state": "off"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.update),
                autospec=True)
    def test_vm_power_on_when_deadlock_raises_once(self, model_update_mock):
        models.VM(uuid=UUID1, name="old", state="off").save()
        response = requests.post(
            self.get_endpoint(TEMPL_POWERON_ACTION_ENDPOINT, UUID1))
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "uuid": UUID1, "name": "old", "state": "on"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update")
    def test_vm_power_off_when_deadlock_raises(self, model_update_mock):
        model_update_mock.side_effect = DEADLOCK_EXC
        models.VM(uuid=UUID1, name="old", state="on").save()
        response = requests.post(
            self.get_endpoint(TEMPL_POWEROFF_ACTION_ENDPOINT, UUID1))
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "uuid": UUID1, "name": "old", "state": "on"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.update),
                autospec=True)
    def test_vm_power_off_when_deadlock_raises_once(self, model_update_mock):
        models.VM(uuid=UUID1, name="old", state="on").save()
        response = requests.post(
            self.get_endpoint(TEMPL_POWEROFF_ACTION_ENDPOINT, UUID1))
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.VM.objects.get_one(filters={
            "uuid": UUID1, "name": "old", "state": "off"}))


class TestRetryOnErrorMiddlewareNestedResourceTestCase(BaseResourceTestCase):

    __LAST_MIGRATION__ = (
        "c17a60-0002-0-rest-service-data-for-test-nested-resource"
    )

    def setUp(self):
        super(TestRetryOnErrorMiddlewareNestedResourceTestCase, self).setUp()

        self.vm1 = models.VM.objects.get_one(filters={
            'uuid': filters.EQ(UUID1)
        })

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.insert",
                side_effect=DEADLOCK_EXC)
    def test_create_port_when_deadlock_raises(self, model_insert_mock):
        response = requests.post(
            self.get_endpoint(TEMPL_PORTS_COLLECTION_ENDPOINT, UUID1),
            json={"mac": "00:00:00:00:00:01"})
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_insert_mock.call_count)
        self.assertEqual(0, len(models.Port.objects.get_all()))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.insert",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.insert),
                autospec=True)
    def test_create_port_when_deadlock_raises_once(self, model_insert_mock):
        response = requests.post(
            self.get_endpoint(TEMPL_PORTS_COLLECTION_ENDPOINT, UUID1),
            json={"mac": "00:00:00:00:00:01"})
        self.assertEqual(201, response.status_code)
        self.assertEqual(2, model_insert_mock.call_count)
        self.assertIsNotNone(models.Port.objects.get_one(filters={
            "mac": "00:00:00:00:00:01"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update",
                side_effect=DEADLOCK_EXC)
    def test_update_port_when_deadlock_raises(self, model_update_mock):
        models.Port(uuid=UUID3, mac="00:00:00:00:00:03", vm=self.vm1).save()
        response = requests.put(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT, UUID1, UUID3),
            json={"mac": "00:00:00:00:00:04"})
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.Port.objects.get_one(filters={
            "uuid": UUID3, "mac": "00:00:00:00:00:03"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.update",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.update),
                autospec=True)
    def test_update_port_when_deadlock_raises_once(self, model_update_mock):
        models.Port(uuid=UUID3, mac="00:00:00:00:00:03", vm=self.vm1).save()
        response = requests.put(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT, UUID1, UUID3),
            json={"mac": "00:00:00:00:00:04"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, model_update_mock.call_count)
        self.assertIsNotNone(models.Port.objects.get_one(filters={
            "uuid": UUID3, "mac": "00:00:00:00:00:04"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.delete",
                side_effect=DEADLOCK_EXC)
    def test_delete_port_when_deadlock_raises(self, model_delete_mock):
        models.Port(uuid=UUID3, mac="00:00:00:00:00:03", vm=self.vm1).save()
        response = requests.delete(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT, UUID1, UUID3))
        self.assertEqual(500, response.status_code)
        self.assertEqual(DEADLOCK_RESPONSE, response.json())
        self.assertEqual(2, model_delete_mock.call_count)
        self.assertIsNotNone(models.Port.objects.get_one(filters={
            "uuid": UUID3, "mac": "00:00:00:00:00:03"}))

    @mock.patch("restalchemy.storage.sql.tables.SQLTable.delete",
                side_effect=partial(raise_deadlock_exc_once,
                                    collections.Counter(), SQLTable.delete),
                autospec=True)
    def test_delete_port_when_deadlock_raises_once(self, model_delete_mock):
        models.Port(uuid=UUID3, mac="00:00:00:00:00:03", vm=self.vm1).save()
        response = requests.delete(
            self.get_endpoint(TEMPL_PORT_RESOURCE_ENDPOINT, UUID1, UUID3))
        self.assertEqual(204, response.status_code)
        self.assertEqual(2, model_delete_mock.call_count)
        self.assertEqual(0, len(models.Port.objects.get_all()))
