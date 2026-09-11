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

import mock


def request_mock(**kwargs):
    """A stand-in request whose context answers the visibility call.

    A resource asks the context which fields the caller wants shown, for
    all of them at once; a bare `Mock` answers with a `Mock`, which is
    not a set of names.
    """
    req = mock.Mock(**kwargs)
    req.api_context.shown_fields.side_effect = frozenset
    req.api_context.resolved_visibilities = {}
    return req
