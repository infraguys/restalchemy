#    Copyright 2026 Genesis Corporation.
#
#    All Rights Reserved.
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

"""Two things a release should not be allowed to lose quietly.

Speed, measured against the floor rather than against a number: what the
same three requests cost when psycopg and orjson serve them with no
framework at all. A ratio, not microseconds, is what a build machine can
be held to -- it is slow for the floor too.

And memory: a request that keeps something is a service that has to be
restarted, and nothing about it shows up in a suite that serves each
request once.

Both are measured in a process of its own; see the probe for why.
"""

import os
import subprocess
import sys
import unittest
from urllib import parse

import orjson

from restalchemy.tests.functional import base
from restalchemy.tests.functional import consts

PROBE = "restalchemy.tests.functional.perf.probe"
TIMEOUT = 600

# How much of the floor's time a request of ours may take, per request.
# Measured on a quiet machine, PostgreSQL on a local socket: 1.6× for a
# collection, 2.1× for a resource, 1.9× for a create. The room above
# those is for the machine, not for us -- a shared runner is worse at
# our Python than at the database's C, so the same code reads higher
# there. Set RA_PERF_RATIO_SLACK to widen it without touching this.
LIMIT = {
    "collection": 2.5,
    "resource": 3.0,
    "create": 3.0,
}
SLACK = float(os.environ.get("RA_PERF_RATIO_SLACK", "1.0"))

# What a request may leave behind. Measured: no objects at all, and
# under 5 bytes -- a cache still settling, not a request's doing. A
# leaked model or document would be tens of objects and hundreds of
# bytes per request.
MAX_OBJECTS_PER_REQUEST = 0.25
MAX_BYTES_PER_REQUEST = 32

# What a cluster that has run out of clients says, in psycopg's words
# and in the pool's.
SHORTAGE = ("too many clients", "PoolTimeout", "connection failed")

SKIPPED = os.environ.get("RA_PERF_SKIP", "")
DIALECT = parse.urlparse(consts.DATABASE_URI).scheme


def probe(mode, *options):
    """Run a measurement and bring back what it answered."""
    command = [sys.executable, "-m", PROBE, "--mode", mode] + list(options)
    environment = dict(os.environ, DATABASE_URI=consts.get_database_uri())
    finished = subprocess.run(
        command,
        capture_output=True,
        timeout=TIMEOUT,
        env=environment,
        check=False,
    )
    if finished.returncode != 0:
        trouble = finished.stderr.decode(errors="replace")
        if any(sign in trouble for sign in SHORTAGE):
            # Not a regression of ours: ten workers of this suite and a
            # guard beside them outran what the cluster will hand out.
            # The probe already waits for a connection to come free;
            # past that, saying so is better than blaming the code.
            raise unittest.SkipTest(
                f"the database had no connection to spare:\n{trouble[-2000:]}"
            )
        raise AssertionError(
            f"the {mode} probe failed ({finished.returncode}):\n{trouble}"
        )
    return orjson.loads(finished.stdout)


@unittest.skipIf(SKIPPED, "RA_PERF_SKIP is set")
@unittest.skipUnless(
    DIALECT == "postgresql",
    f"the floor is a raw psycopg one; this run is against {DIALECT}",
)
class PerfGuardTestCase(base.BaseFunctionalTestCase):
    def test_a_request_stays_near_the_floor(self):
        exceeded, answer = self._exceeded(probe("speed"))
        if exceeded:
            # Measured again before anything is called a regression: one
            # busy moment on a shared machine is not one.
            exceeded, answer = self._exceeded(probe("speed"))
        self.assertFalse(exceeded, self._speed_report(answer, exceeded))

    def test_a_request_keeps_nothing(self):
        answer = probe("memory")
        per_request = answer["per_request"]
        self.assertLessEqual(
            per_request["objects"],
            MAX_OBJECTS_PER_REQUEST,
            self._memory_report(answer, "objects"),
        )
        self.assertLessEqual(
            per_request["bytes"],
            MAX_BYTES_PER_REQUEST,
            self._memory_report(answer, "bytes"),
        )

    @staticmethod
    def _exceeded(answer):
        over = {
            scenario: ratio
            for scenario, ratio in answer["ratio"].items()
            if ratio > LIMIT[scenario] * SLACK
        }
        return over, answer

    @staticmethod
    def _speed_report(answer, exceeded):
        lines = [
            (
                "a request costs more of the floor than it may"
                f" ({answer['rounds']} rounds, best of {answer['calls']} calls,"
                f" {answer['rows']} rows, page {answer['page']}):"
            )
        ]
        for scenario, ratio in answer["ratio"].items():
            over = "  <-- over" if scenario in exceeded else ""
            lines.append(
                f"  {scenario:<11} floor {answer['floor'][scenario]:6.0f} µs,"
                f" ours {answer['restalchemy'][scenario]:6.0f} µs,"
                f" {ratio:.2f}× (at most {LIMIT[scenario] * SLACK:.2f}×){over}"
            )
        return "\n".join(lines)

    @staticmethod
    def _memory_report(answer, what):
        lines = [
            (
                f"a request keeps {what}:"
                f" {answer['per_request'][what]:.2f} per request"
                f" over the last {answer['served']} of them"
            )
        ]
        for step in answer["series"]:
            lines.append(
                f"  after {step['requests']:5d} requests:"
                f" {step['objects']:6d} objects, {step['bytes']:8d} bytes"
            )
        return "\n".join(lines)
