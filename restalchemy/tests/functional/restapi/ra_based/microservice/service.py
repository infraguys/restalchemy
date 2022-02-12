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

import threading
from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIServer

from restalchemy.api import applications
from restalchemy.api.middlewares import errors as errors_middleware
from restalchemy.storage.sql import engines
from restalchemy.tests.functional import consts
from restalchemy.tests.functional.restapi.ra_based.microservice import (
    middlewares)
from restalchemy.tests.functional.restapi.ra_based.microservice import routes


class RESTService(threading.Thread):

    def __init__(self, bind_host="127.0.0.1", bind_port=8080):
        super(RESTService, self).__init__(name="REST Service")

        self._httpd = make_server(
            bind_host, bind_port,
            errors_middleware.ErrorsHandlerMiddleware(
                middlewares.ContextMiddleware(
                    application=applications.Application(routes.Root))
            ),
            WSGIServer)

    def run(self):
        self._httpd.serve_forever()

    def stop(self):
        self._httpd.server_close()
        self._httpd.shutdown()
        self.join(timeout=10)


def main():
    rest_service = RESTService()
    try:
        rest_service.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    engines.engine_factory.configure_factory(consts.DATABASE_URI)
    main()
