# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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
"""Batch requests example client.

Run restapi_foo_bar_service.py first, then run this script against it:

    python examples/restapi_foo_bar_service.py &
    python examples/restapi_batch_client.py

See docs/en/how-to/api-batch-requests.md for the full request/response
format -- every item is best-effort and independent, dispatched through
the full middleware stack (so no cross-item transaction).

Note: a batch item cannot reference another item's result (e.g. a
server-generated uuid) -- that's a deliberate restriction, see "Explicit
non-goals" in the how-to guide. So the two Foo resources created below are
independent of each other; if you need the uuid a batch item produced,
read it from *this script's* response handling, same as any other client
code, and use it in a later request.
"""

import json

import requests

BATCH_URL = "http://127.0.0.1:8000/batch/"
headers = {"content-type": "application/json", "cache-control": "no-cache"}


# -----------------------------------------------------------------------------
# Create two independent Foo resources in a single HTTP call.
# -----------------------------------------------------------------------------

payload = {
    "requests": [
        {
            "method": "POST",
            "path": "/v1/foos/",
            "body": {"foo-field1": 1, "foo-field2": "foo obj 1"},
        },
        {
            "method": "POST",
            "path": "/v1/foos/",
            "body": {"foo-field1": 2, "foo-field2": "foo obj 2"},
        },
    ],
}

print("Make POST request to %s with payload %s" % (BATCH_URL, payload))
response = requests.post(BATCH_URL, json=payload, headers=headers)
print("Response status: %s" % response.status_code)
results = response.json()
print(json.dumps(results, indent=2))

foo_uuid = results[0]["body"]["uuid"]


# -----------------------------------------------------------------------------
# Best-effort mode: one item fails (unknown Foo uuid), the rest still
# succeed. The outer HTTP call is still 200 OK -- check each item's own
# "status" instead of relying on the outer response status.
# -----------------------------------------------------------------------------

payload = {
    "requests": [
        {"method": "GET", "path": "/v1/foos/%s" % foo_uuid},
        {"method": "GET", "path": "/v1/foos/00000000-0000-0000-0000-000000000000"},
    ],
}

print("\nMake POST request to %s with payload %s" % (BATCH_URL, payload))
response = requests.post(BATCH_URL, json=payload, headers=headers)
print("Response status: %s" % response.status_code)
results = response.json()
print(json.dumps(results, indent=2))
assert results[0]["status"] == 200
assert results[1]["status"] == 404
print("First item succeeded, second failed, and the outer call still returned 200.")
