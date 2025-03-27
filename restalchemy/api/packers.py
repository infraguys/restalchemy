#    Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
#    Copyright 2021 Eugene Frolov.
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

import collections
import copy
import json
import logging
import types

from restalchemy.api import constants
from restalchemy.common import exceptions
from restalchemy.common import utils

DEFAULT_VALUE = object()
CONTENT_TYPE_APPLICATION_JSON = DEFAULT_CONTENT_TYPE = (
    constants.CONTENT_TYPE_APPLICATION_JSON
)  # noqa

LOG = logging.getLogger(__name__)


def get_content_type(headers):
    return headers.get("Content-Type") or constants.DEFAULT_CONTENT_TYPE


class BaseResourcePacker(object):

    _skip_none = True

    def __init__(self, resource_type, request):
        self._rt = resource_type
        self._req = request

    def pack_resource(self, obj):
        if isinstance(
            obj,
            (str, int, float, bool, type(None), list, tuple, dict),
        ):
            return obj
        else:
            result = {}
            for name, prop in self._rt.get_fields_by_request(self._req):
                api_name = prop.api_name
                if (
                    prop.is_public()
                    and not self._rt._fields_permissions.is_hidden(
                        name, self._req
                    )
                ):
                    value = getattr(obj, name)
                    if value is None:
                        if not self._skip_none:
                            result[api_name] = value
                    else:
                        result[api_name] = prop.dump_value(value)

            return result

    def pack(self, obj):
        if isinstance(obj, list) or isinstance(obj, types.GeneratorType):
            return [self.pack_resource(resource) for resource in obj]
        else:
            return self.pack_resource(obj)

    @utils.raise_parse_error_on_fail
    def _parse_value(self, name, value, prop):
        return prop.parse_value(self._req, value)

    def unpack(self, value):
        if not self._rt:
            return value
        value = copy.deepcopy(value)
        result = {}
        for name, prop in self._rt.get_fields_by_request(self._req):
            api_name = prop.api_name
            prop_value = value.pop(api_name, DEFAULT_VALUE)
            if prop_value is not DEFAULT_VALUE:
                if not prop.is_public():
                    raise exceptions.ValidationPropertyPrivateError(
                        property=api_name
                    )

                if self._rt._fields_permissions.is_readonly(name, self._req):
                    raise exceptions.FieldPermissionError(field=name)
                result[name] = self._parse_value(api_name, prop_value, prop)

        if len(value) > 0:
            raise exceptions.ValidationPropertyIncompatibleError(
                val=value, model=self._rt.get_model().__name__
            )

        return result


class JSONPacker(BaseResourcePacker):

    def pack(self, obj):
        return json.dumps(super(JSONPacker, self).pack(obj))

    def unpack(self, value):
        if isinstance(value, bytes):
            try:
                return super(JSONPacker, self).unpack(
                    json.loads(value.decode("utf-8")),
                )
            except json.decoder.JSONDecodeError:
                raise exceptions.ParseBodyError()

        return super(JSONPacker, self).unpack(json.loads(value))


class JSONPackerIncludeNullFields(JSONPacker):

    _skip_none = False


class MultipartPacker(JSONPacker):
    """
    This packer is specifically designed to handle multipart/form-data
    requests, which are commonly used for uploading files.
    It ensures that only file-related data is extracted and processed,
    allowing for seamless integration with file upload or download function.

    Key Features:
    - Supports only file uploads by default.
    - If future requirements extend the support to include model JSON under
      a specific key, it may be updated accordingly.
    - Extracts file data into a structured dictionary where each file is
      identified by its part name.
    - Uses '_multipart' as a flag to indicate that multipart content was used
      for processing.
    """

    # TODO: as of now this packer support only file uploads.
    #  In future model's json should be under this field name
    # _resource_key = "_resource"
    _multipart_key = "multipart"
    _parts_key = "parts"

    def _unpack_multipart(self):
        """
        Unpacks multipart/form-data request into a structured dictionary.

        :return: A dictionary containing the following keys:
            - 'multipart': A boolean flag indicating that multipart content
              was found.
            - 'parts': A dictionary where each key is the part field name and
              the corresponding value is the file data (bytes)
              (as `FieldStorage()`).
        """
        result = collections.defaultdict(dict)
        result[self._multipart_key] = True

        # if self._resource_key not in self._req.POST:
        #     ValueError("Resource data should be under '_resource' part!")
        #     result[self._resource_key] = super().unpack(self._req.POST['self._resource_key'])

        for key, part in self._req.POST.items():
            # if key == self._resource_key:
            #     continue
            result[self._parts_key][key] = part

        return result

    def unpack(self, value):
        if constants.CONTENT_TYPE_MULTIPART in self._req.content_type:
            return self._unpack_multipart()
        return super().unpack(value)

    def pack(self, obj):
        if isinstance(obj, bytes):
            return obj
        return super().pack(obj)


packer_mapping = {
    constants.CONTENT_TYPE_APPLICATION_JSON: JSONPacker,
    constants.CONTENT_TYPE_MULTIPART: MultipartPacker,
}


def parse_content_type(value):
    # Cleanup: application/json;charset=UTF-8
    return value.split(";")[0].strip() if value else None


def get_packer(content_type):
    try:
        return packer_mapping[parse_content_type(content_type)]
    except KeyError:
        # TODO(Eugene Frolov): Specify Exception Type and message
        raise Exception(
            "Packer can't found for content type %s " % content_type
        )


def set_packer(content_type, packer_class):
    packer_mapping[content_type] = packer_class
