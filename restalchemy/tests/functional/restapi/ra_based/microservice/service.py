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

import threading
from wsgiref import simple_server

from restalchemy.api import applications
from restalchemy.api.middlewares import (
    retry_on_error as retry_error_middleware,
)

from restalchemy.api.middlewares import errors as errors_middleware
from restalchemy.openapi import engines as openapi_engines
from restalchemy.openapi import structures as openapi_structures
from restalchemy.storage import exceptions as storage_exc
from restalchemy.storage.sql import engines
from restalchemy.tests.functional import consts
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    middlewares,
)
from restalchemy.tests.functional.restapi.ra_based.microservice import routes


class RESTService(threading.Thread):

    def __init__(self, bind_host, bind_port, app_root):
        super(RESTService, self).__init__(name="REST Service")

        self._service_port = bind_port
        self._service_host = bind_host

        self._httpd = simple_server.make_server(
            bind_host,
            bind_port,
            app_root,
            simple_server.WSGIServer,
        )

    @property
    def service_port(self):
        return self._service_port

    @property
    def service_host(self):
        return self._service_host

    def run(self):
        self._httpd.serve_forever()

    def stop(self):
        self._httpd.server_close()
        self._httpd.shutdown()
        self.join(timeout=10)


def build_wsgi_application(app_root):
    openapi_engine = openapi_engines.OpenApiEngine(
        info=openapi_structures.OpenApiInfo(
            title="REST API Microservice",
            description="REST API Microservice for tests",
            version="1.2.3",
            contact=openapi_structures.OpenApiContact(
                name="Functional Tests",
                url="https://functional.tests/",
                email="functional@tests.local",
            ),
            license=openapi_structures.OpenApiApacheLicense(),
            terms_of_service="https://functional.tests/terms/",
        ),
        paths=openapi_structures.OpenApiPaths(),
        components=openapi_structures.OpenApiComponents(),
        security=[openapi_structures.OpenApiSecurity()],
        tags=openapi_structures.OpenApiTags(
            [
                openapi_structures.OpenApiTag(
                    name="functional-test",
                    description="Just functional tests",
                    external_docs=openapi_structures.OpenApiExternalDocs(
                        url="https://https://functional.tests/docs/",
                        description=(
                            "Functional tests external documentation"
                        ),
                    ),
                )
            ]
        ),
        external_docs=openapi_structures.OpenApiExternalDocs(
            url="https://https://functional.tests/docs/",
            description="Functional tests external documentation",
        ),
    )

    return errors_middleware.ErrorsHandlerMiddleware(
        retry_error_middleware.RetryOnErrorsMiddleware(
            middlewares.ContextMiddleware(
                application=applications.OpenApiApplication(
                    route_class=app_root,
                    openapi_engine=openapi_engine,
                ),
            ),
            exceptions=storage_exc.DeadLock,
            # set max_retry == 2 to speed up retry tests
            # execution
            max_retry=2,
        ),
    )


def main():
    rest_service = RESTService(
        bind_host="0.0.0.0",
        bind_port=8000,
        app_root=build_wsgi_application(app_root=routes.Root),
    )
    try:
        rest_service.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    engines.engine_factory.configure_factory(consts.DATABASE_URI)
    main()
