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

"""In-process store for generated OpenAPI specifications.

Generating the document walks every route and every model, which is far too
much work to repeat per request, but the result is only valid for the code
currently loaded. Keeping it in the process ties both facts together: it is
built at most once, and a restart -- which is what an upgrade ends with --
throws it away.

The store is module level rather than per application on purpose. A service
that runs several workers builds one application object per worker before
forking, so an application-scoped cache would be filled once per worker; here
the first one to build fills it for all of them, and the children inherit it
through the fork.
"""

import logging
import typing

LOG = logging.getLogger(__name__)

_SPECIFICATIONS: typing.Dict[typing.Tuple[str, str], typing.Any] = {}

# The same documents, already serialized, keyed additionally by the host they
# were rendered for: that is the one thing in them that varies per caller.
# Serving these avoids encoding a few hundred kilobytes on every request.
_ENCODED: typing.Dict[typing.Tuple[str, str, str], bytes] = {}


def _application_key(application: typing.Any) -> str:
    """Name the application, so unrelated services never share an entry."""
    main_route = application.main_route
    return "%s.%s" % (main_route.__module__, main_route.__qualname__)


def load(application: typing.Any, version: str) -> typing.Any:
    return _SPECIFICATIONS.get((_application_key(application), version))


def store(application: typing.Any, version: str, specification: typing.Any) -> None:
    key = _application_key(application)
    _SPECIFICATIONS[(key, version)] = specification
    # Whatever was encoded describes the previous document.
    for encoded_key in [
        encoded_key
        for encoded_key in _ENCODED
        if encoded_key[0] == key and encoded_key[1] == version
    ]:
        del _ENCODED[encoded_key]


def load_encoded(application: typing.Any, version: str, host: str) -> typing.Any:
    return _ENCODED.get((_application_key(application), version, host))


def store_encoded(
    application: typing.Any, version: str, host: str, body: bytes
) -> None:
    _ENCODED[(_application_key(application), version, host)] = body


def clear() -> None:
    _SPECIFICATIONS.clear()
    _ENCODED.clear()


def warm_up(application: typing.Any, request: typing.Any) -> None:
    """Build every supported specification ahead of the first request.

    Called while the application is being constructed, so a service that forks
    its workers pays for this once and every worker starts with the document
    ready. Failure is not fatal: whatever goes wrong here would go wrong again
    on the first request, and a documentation endpoint must not be the reason a
    service refuses to start.
    """
    engine = application.openapi_engine
    if engine is None:
        return
    for version in engine.list_supported_openapi_versions():
        if load(application, version) is not None:
            continue
        try:
            store(
                application,
                version,
                engine.build_openapi_specification(version=version, request=request),
            )
        except Exception:
            LOG.warning(
                "Could not prepare the OpenAPI %s specification at startup; "
                "it will be built on the first request instead",
                version,
                exc_info=True,
            )
