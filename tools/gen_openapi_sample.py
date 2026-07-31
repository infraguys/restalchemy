"""Generate the OpenAPI spec of the functional-test microservice, offline.

Boots the test WSGI app in-process (no DB, no socket) and dumps the spec, so
the effect of generator changes can be measured, and the checked-in snapshots
under tests/functional/.../microservice/ refreshed, without a functional run.

    python tools/gen_openapi_sample.py 3.1.0 > openapi_310.yaml
"""

import os
import sys

import webob
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from restalchemy.openapi import constants as oa_c  # noqa: E402
from restalchemy.tests.functional.restapi.ra_based.microservice import (  # noqa: E402
    routes as test_routes,
)
from restalchemy.tests.functional.restapi.ra_based.microservice import (  # noqa: E402
    service as test_service,
)


def build_spec(version):
    app = test_service.build_wsgi_application(app_root=test_routes.Root)
    # PUT regenerates unconditionally; GET would serve the /tmp spec cache.
    req = webob.Request.blank("/specifications/%s" % version)
    req.method = "PUT"
    req.content_type = "application/json"
    req.body = b"{}"
    resp = req.get_response(app)
    if resp.status_code != 200:
        sys.stderr.write("%s\n%s\n" % (resp.status, resp.text[:2000]))
        raise SystemExit(1)
    return resp.json


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else oa_c.OPENAPI_SPECIFICATION_3_1_0
    yaml.safe_dump(
        build_spec(version), sys.stdout, default_flow_style=False, sort_keys=True
    )


if __name__ == "__main__":
    main()
