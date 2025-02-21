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

import requests


# -----------------------------------------------------------------------------
# List API versions
# -----------------------------------------------------------------------------

url = "http://127.0.0.1:8000/"
headers = {"cache-control": "no-cache"}
print("Make GET request to %s" % url)
response = requests.request("GET", url, headers=headers)
print("Response is %s. Headers is %s" % (response.text, response.headers))


# -----------------------------------------------------------------------------
# Create Foo resource
# -----------------------------------------------------------------------------

url = "http://127.0.0.1:8000/foos/"
payload = {"foo-field1": 999, "foo-field2": "foo obj"}
headers = {"content-type": "application/json", "cache-control": "no-cache"}
print("Make POST request to %s with payload %s" % (url, payload))
response = requests.request("POST", url, json=payload, headers=headers)
print("Response is %s. Headers is %s" % (response.text, response.headers))

foo_uuid = response.json()["uuid"]


# -----------------------------------------------------------------------------
# Get list of Foo resources
# -----------------------------------------------------------------------------

url = "http://127.0.0.1:8000/foos/"
headers = {"cache-control": "no-cache"}
print("Make GET (list on collection) request to %s" % url)
response = requests.request("GET", url, headers=headers)
print("Response is %s. Headers is %s" % (response.text, response.headers))


# -----------------------------------------------------------------------------
# Get Foo resource by uuid
# -----------------------------------------------------------------------------

url = "http://127.0.0.1:8000/foos/%s" % foo_uuid
headers = {"cache-control": "no-cache"}
print("Make GET request to foo resource %s" % url)
response = requests.request("GET", url, headers=headers)

print("Response is %s. Headers is %s" % (response.text, response.headers))


# -----------------------------------------------------------------------------
# Create Bar resource
# -----------------------------------------------------------------------------

url = "http://127.0.0.1:8000/foos/%s/bars/" % foo_uuid

payload = {"bar-field1": "test bar"}
headers = {
    "content-type": "application/json",
    "cache-control": "no-cache",
}
print("Make POST request to %s with payload %s" % (url, payload))
response = requests.request("POST", url, json=payload, headers=headers)
print("Response is %s. Headers is %s" % (response.text, response.headers))


bar_uuid = response.json()["uuid"]


# -----------------------------------------------------------------------------
# Delete Bar resource
# -----------------------------------------------------------------------------

url = "http://127.0.0.1:8000/bars/%s" % bar_uuid
headers = {"cache-control": "no-cache"}
print("Make DELETE request to %s" % url)
response = requests.request("DELETE", url, headers=headers)
print("Done!")
