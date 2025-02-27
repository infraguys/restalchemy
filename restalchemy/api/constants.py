#    Copyright 2021 Eugene Frolov.
#
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

# HTTP methods
GET = "GET"
PUT = "PUT"
POST = "POST"

# RA methods
FILTER = "FILTER"
CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"

# RA action methods
ACTION_GET = "ACTION_GET"
ACTION_POST = "ACTION_POST"
ACTION_PUT = "ACTION_PUT"

# all RA methods
ALL = "ALL"

ALL_RA_METHODS = [
    GET,  # Controller.get
    FILTER,  # Controller.filter
    CREATE,  # Controller.create
    UPDATE,  # Controller.update
    DELETE,  # Controller.delete
    ACTION_GET,  # Action.get
    ACTION_POST,  # Action.post
    ACTION_PUT,  # Action.put
    ALL,  # All RA methods + actions
]


HTTP_TO_RA_COLLECTION_METHODS = {GET: FILTER, POST: CREATE}
HTTP_TO_RA_RESOURCE_METHODS = {GET: GET, PUT: UPDATE, DELETE: DELETE}

CONTENT_TYPE_APPLICATION_JSON = DEFAULT_CONTENT_TYPE = "application/json"
CONTENT_TYPE_MULTIPART = "multipart/form-data"
CONTENT_TYPE_OCTET_STREAM = "application/octet-stream"
