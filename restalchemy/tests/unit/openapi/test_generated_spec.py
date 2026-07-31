# Copyright 2026 Eugene Frolov <eugene@frolov.net.ru>
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

"""Structural checks on the spec the generator produces.

These do not need a database or a running service: the functional-test
microservice is driven in-process through WSGI.
"""

import collections
import unittest

import webob

from restalchemy.openapi import constants as oa_c
from restalchemy.tests.functional.restapi.ra_based.microservice import routes
from restalchemy.tests.functional.restapi.ra_based.microservice import service


def build_spec(version):
    app = service.build_wsgi_application(app_root=routes.Root)
    # PUT regenerates; GET would answer from the on-disk spec cache.
    request = webob.Request.blank("/specifications/%s" % version)
    request.method = "PUT"
    request.content_type = "application/json"
    request.body = b"{}"
    response = request.get_response(app)
    if response.status_code != 200:
        raise AssertionError(
            "spec generation failed: %s %s" % (response.status, response.text[:500])
        )
    return response.json


def collect_refs(node):
    refs = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                refs.append(value)
            else:
                refs.extend(collect_refs(value))
    elif isinstance(node, list):
        for item in node:
            refs.extend(collect_refs(item))
    return refs


def resolve(spec, ref):
    node = spec
    for part in ref.lstrip("#/").split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


class GeneratedSpecTestCase(unittest.TestCase):
    VERSIONS = (
        oa_c.OPENAPI_SPECIFICATION_3_0_3,
        oa_c.OPENAPI_SPECIFICATION_3_1_0,
    )

    def test_every_local_ref_resolves(self):
        for version in self.VERSIONS:
            spec = build_spec(version)
            broken = sorted(
                {
                    ref
                    for ref in collect_refs(spec)
                    if ref.startswith("#/") and resolve(spec, ref) is None
                }
            )
            self.assertEqual([], broken, "dangling $refs in %s spec" % version)

    def test_operation_ids_are_unique(self):
        for version in self.VERSIONS:
            spec = build_spec(version)
            seen = collections.Counter()
            for path, item in spec["paths"].items():
                for method, operation in item.items():
                    if isinstance(operation, dict) and "operationId" in operation:
                        seen[operation["operationId"]] += 1
            duplicates = sorted(name for name, n in seen.items() if n > 1)
            self.assertEqual(
                [], duplicates, "duplicate operationIds in %s spec" % version
            )

    def test_numeric_bounds_are_well_formed(self):
        # exclusiveMaximum/exclusiveMinimum without the matching bound is
        # invalid under the 3.0.3 dialect, and must be a number in 3.1.0.
        offenders = []

        def walk(node, path):
            if isinstance(node, dict):
                for exclusive, inclusive in (
                    ("exclusiveMaximum", "maximum"),
                    ("exclusiveMinimum", "minimum"),
                ):
                    if exclusive in node and isinstance(node[exclusive], bool):
                        if inclusive not in node:
                            offenders.append("%s/%s" % (path, exclusive))
                for key, value in node.items():
                    walk(value, "%s/%s" % (path, key))
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, "%s/%d" % (path, i))

        for version in self.VERSIONS:
            offenders = []
            walk(build_spec(version), "")
            self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
