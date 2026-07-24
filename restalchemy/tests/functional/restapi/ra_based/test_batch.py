# Copyright 2026 George Melikov
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

import contextlib
import socket
from urllib import parse
import uuid as pyuuid

import requests

from restalchemy.api import batch
from restalchemy.api import middlewares
from restalchemy.common import utils
from restalchemy.storage import exceptions
from restalchemy.tests.functional import base
from restalchemy.tests.functional.restapi.ra_based import test_resources
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    routes as microservice_routes,
)
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    service as microservice_service,
)
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    storable_models as models,
)

TEMPL_BATCH_ENDPOINT = utils.lastslash(
    parse.urljoin(test_resources.TEMPL_SERVICE_ENDPOINT, "batch")
)

UUID1 = pyuuid.UUID("00000000-0000-0000-0000-000000000001")
UUID2 = pyuuid.UUID("00000000-0000-0000-0000-000000000002")
UNKNOWN_UUID = pyuuid.UUID("00000000-0000-0000-0000-0000000000ff")


class TestBatchTestCase(test_resources.BaseResourceTestCase):
    def _insert_vm_to_db(self, uuid, name, state):
        vm = models.VM(uuid=uuid, name=name, state=state)
        vm.save()
        return vm

    def _vm_exists_in_db(self, uuid):
        try:
            models.VM.objects.get_one(filters={"uuid": uuid})
            return True
        except exceptions.RecordNotFound:
            return False

    def _post_batch(self, requests_):
        return requests.post(
            self.get_endpoint(TEMPL_BATCH_ENDPOINT),
            json={"requests": requests_},
        )

    def test_root_lists_batch_route(self):
        response = requests.get(
            self.get_endpoint(test_resources.TEMPL_ROOT_COLLECTION_ENDPOINT)
        )

        self.assertEqual(200, response.status_code)
        self.assertIn("batch", response.json())

    def test_create_two_vms_in_one_batch(self):
        response = self._post_batch(
            [
                {"method": "POST", "path": "/v1/vms/", "body": {"name": "vm-a"}},
                {"method": "POST", "path": "/v1/vms/", "body": {"name": "vm-b"}},
            ]
        )

        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertEqual(2, len(results))
        self.assertEqual(201, results[0]["status"])
        self.assertEqual(201, results[1]["status"])
        self.assertEqual("vm-a", results[0]["body"]["name"])
        self.assertEqual("vm-b", results[1]["body"]["name"])
        self.assertTrue(self._vm_exists_in_db(results[0]["body"]["uuid"]))
        self.assertTrue(self._vm_exists_in_db(results[1]["body"]["uuid"]))

    def test_mixed_get_update_delete_in_one_batch(self):
        self._insert_vm_to_db(uuid=UUID1, name="old", state="off")

        response = self._post_batch(
            [
                {"method": "GET", "path": "/v1/vms/%s" % UUID1},
                {
                    "method": "PUT",
                    "path": "/v1/vms/%s" % UUID1,
                    "body": {"name": "new"},
                },
                {"method": "DELETE", "path": "/v1/vms/%s" % UUID1},
            ]
        )

        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertEqual(200, results[0]["status"])
        self.assertEqual("old", results[0]["body"]["name"])
        self.assertEqual(200, results[1]["status"])
        self.assertEqual("new", results[1]["body"]["name"])
        self.assertIn(results[2]["status"], (200, 204))
        self.assertFalse(self._vm_exists_in_db(UUID1))

    def test_action_invoke_in_batch(self):
        self._insert_vm_to_db(uuid=UUID1, name="test", state="off")

        response = self._post_batch(
            [
                {
                    "method": "POST",
                    "path": "/v1/vms/%s/actions/poweron/invoke" % UUID1,
                }
            ]
        )

        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertEqual(200, results[0]["status"])
        self.assertEqual("on", results[0]["body"]["state"])
        vm = models.VM.objects.get_one(filters={"uuid": UUID1})
        self.assertEqual("on", vm.state)

    def test_best_effort_partial_failure_does_not_block_siblings(self):
        self._insert_vm_to_db(uuid=UUID1, name="test", state="off")

        response = self._post_batch(
            [
                {"method": "GET", "path": "/v1/vms/%s" % UUID1},
                {"method": "GET", "path": "/v1/vms/%s" % UNKNOWN_UUID},
                {
                    "method": "PUT",
                    "path": "/v1/vms/%s" % UUID1,
                    "body": {"name": "updated"},
                },
            ],
        )

        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertEqual(200, results[0]["status"])
        self.assertEqual(404, results[1]["status"])
        self.assertEqual(200, results[2]["status"])
        vm = models.VM.objects.get_one(filters={"uuid": UUID1})
        self.assertEqual("updated", vm.name)

    def test_query_string_filter_in_batch_item(self):
        self._insert_vm_to_db(uuid=UUID1, name="alpha", state="off")
        self._insert_vm_to_db(uuid=UUID2, name="beta", state="off")

        response = self._post_batch([{"method": "GET", "path": "/v1/vms/?name=alpha"}])

        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertEqual(200, results[0]["status"])
        names = [vm["name"] for vm in results[0]["body"]]
        self.assertEqual(["alpha"], names)

    def test_nested_batch_item_is_rejected(self):
        response = self._post_batch(
            [{"method": "POST", "path": "/batch/", "body": {"requests": []}}]
        )

        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertEqual(400, results[0]["status"])
        self.assertIn("batch", results[0]["body"]["message"])

    def test_batch_size_limit_is_enforced(self):
        requests_ = [{"method": "GET", "path": "/v1/vms/"}] * (
            batch.BatchController.__max_batch_size__ + 1
        )

        response = self._post_batch(requests_)

        self.assertEqual(400, response.status_code)
        self.assertIn("exceeds maximum", response.json()["message"])

    def test_requests_must_be_a_list(self):
        response = requests.post(
            self.get_endpoint(TEMPL_BATCH_ENDPOINT),
            json={"requests": {"method": "GET", "path": "/v1/vms/"}},
        )

        self.assertEqual(400, response.status_code)


class _BlockVmWritesMiddleware(middlewares.Middleware):
    """Stand-in for a real auth/policy middleware: rejects POST /v1/vms/."""

    def process_request(self, req):
        if req.method == "POST" and req.path_info.rstrip("/") == "/v1/vms":
            return req.ResponseClass(
                status=403, json={"message": "forbidden by policy"}
            )
        return None


def _build_wsgi_app_with_policy_middleware():
    """Same stack as microservice.service.build_wsgi_application, plus an
    outermost policy middleware -- used to prove batch items are subject to
    the same per-route policy a direct request would get (see
    _BlockVmWritesMiddleware and the regression test below).
    """
    return _BlockVmWritesMiddleware(
        application=microservice_service.build_wsgi_application(
            app_root=microservice_routes.Root,
        ),
    )


class TestBatchMiddlewarePolicyTestCase(base.BaseWithDbMigrationsTestCase):
    __LAST_MIGRATION__ = "0001-rest-service-tables-migration-e31a12"
    __FIRST_MIGRATION__ = "0001-rest-service-tables-migration-e31a12"

    def get_endpoint(self, template, *args):
        return template % ((self.service_port,) + tuple(args))

    def find_free_port(self):
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("127.0.0.1", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def setUp(self):
        super(TestBatchMiddlewarePolicyTestCase, self).setUp()

        self.service_port = self.find_free_port()
        url = parse.urlparse(self.get_endpoint(test_resources.TEMPL_SERVICE_ENDPOINT))
        self._service = microservice_service.RESTService(
            bind_host=url.hostname,
            bind_port=url.port,
            app_root=_build_wsgi_app_with_policy_middleware(),
        )
        self._service.start()

    def tearDown(self):
        super(TestBatchMiddlewarePolicyTestCase, self).tearDown()

        self._service.stop()

    def test_direct_request_is_blocked_by_policy_middleware(self):
        response = requests.post(
            self.get_endpoint(test_resources.TEMPL_VMS_COLLECTION_ENDPOINT),
            json={"name": "should-be-blocked"},
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual(0, len(models.VM.objects.get_all()))

    def test_batch_item_is_blocked_by_the_same_policy_middleware(self):
        """Regression test: batch must dispatch each item through the full
        middleware stack, not just the innermost WSGIApp, so a policy
        middleware wrapping the app (auth, per-route rules, rate limiting,
        ...) applies to a batch item exactly like it would to a direct
        request against that same path.
        """
        response = requests.post(
            self.get_endpoint(TEMPL_BATCH_ENDPOINT),
            json={
                "requests": [
                    {
                        "method": "POST",
                        "path": "/v1/vms/",
                        "body": {"name": "should-be-blocked"},
                    },
                ],
            },
        )

        self.assertEqual(200, response.status_code)
        results = response.json()
        self.assertEqual(403, results[0]["status"])
        self.assertEqual(0, len(models.VM.objects.get_all()))
