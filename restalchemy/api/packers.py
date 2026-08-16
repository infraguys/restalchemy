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
import logging
import types
import typing
import weakref

import orjson

from restalchemy.api import constants
from restalchemy.common import exceptions
from restalchemy.common import utils
from restalchemy.dm import properties as ra_properties

DEFAULT_VALUE = object()
CONTENT_TYPE_APPLICATION_JSON = DEFAULT_CONTENT_TYPE = (
    constants.CONTENT_TYPE_APPLICATION_JSON
)  # noqa

LOG = logging.getLogger(__name__)


def get_content_type(headers):
    return headers.get("Content-Type") or constants.DEFAULT_CONTENT_TYPE


_CLASS_ATTRIBUTE_NAMES = weakref.WeakKeyDictionary()


def _class_attribute_names(klass):
    """Every name the class or one of its bases defines.

    A model's declared properties are not among them -- the metaclass
    moves them off the class -- so this is exactly the set of names a
    model answers with something other than a stored property value.

    Read once per class: a class gains its attributes when it is
    defined. A `@property` added to a model class after something has
    already been packed from it would not be noticed.
    """
    names = _CLASS_ATTRIBUTE_NAMES.get(klass)
    if names is None:
        names = set()
        for base in klass.__mro__:
            names.update(base.__dict__)
        names = frozenset(names)
        _CLASS_ATTRIBUTE_NAMES[klass] = names
    return names


class BaseResourcePacker(object):
    _skip_none = True

    def __init__(self, resource_type, request):
        self._rt = resource_type
        self._req = request
        self._fields = None
        self._visible_fields = None
        self._fields_resource = None
        self._fields_by_model = {}

    def _get_fields(self):
        """The resource fields, resolved once per packer.

        `get_fields_by_request` rebuilds a property object per field on
        every call, and the answer depends only on the request, which a
        packer is built for and does not outlive. Packing a collection
        called it once per object.

        The resource is not as fixed as the request: `routes.Action.do`
        swaps `_rt` out after building the packer, so a cache is only
        good for the resource it was built from.
        """
        if self._fields is None or self._fields_resource is not self._rt:
            self._fields_resource = self._rt
            self._fields = list(self._rt.get_fields_by_request(self._req))
            self._visible_fields = None
            self._fields_by_model = {}
        return self._fields

    def _get_visible_fields(self):
        """The fields packing writes out, with their API names.

        Each carries the call that writes its value out, resolved here
        rather than reached through the field per object: `None` for a
        field whose value is already what goes on the wire.
        """
        fields = self._get_fields()
        if self._visible_fields is None:
            self._visible_fields = [
                (name, prop.api_name, prop.get_dump_callable())
                for name, prop in fields
                if prop.is_public()
                and not self._rt._fields_permissions.is_hidden(name, self._req)
            ]
        return self._visible_fields

    def _get_fields_for_model(self, model_class):
        """The visible fields, saying which are the model's own to read.

        `getattr` on a model property is a failed attribute lookup, a
        `__getattr__` frame and a mapping behind it -- per field per
        object packed. A name the class itself defines (a `@property`
        computing a value, a custom property) is not the model's to hand
        over, and keeps the attribute lookup it has always had.
        """
        fields = self._fields_by_model.get(model_class)
        if fields is None:
            defined = _class_attribute_names(model_class)
            fields = [
                (name, api_name, dump, name not in defined)
                for name, api_name, dump in self._get_visible_fields()
            ]
            self._fields_by_model[model_class] = fields
        return fields

    def pack_resource(self, obj):
        if isinstance(
            obj,
            (str, int, float, bool, type(None), list, tuple, dict),
        ):
            return obj

        obj_properties = getattr(obj, "properties", None)
        if type(obj_properties) is not ra_properties.PropertyManager:
            result = {}
            for name, api_name, dump in self._get_visible_fields():
                value = getattr(obj, name)
                if value is None:
                    if not self._skip_none:
                        result[api_name] = value
                elif dump is None:
                    result[api_name] = value
                else:
                    result[api_name] = dump(value)
            return result

        values = obj_properties._properties
        result = {}
        for name, api_name, dump, own in self._get_fields_for_model(type(obj)):
            prop = values.get(name) if own else None
            value = prop.value if prop is not None else getattr(obj, name)
            if value is None:
                if not self._skip_none:
                    result[api_name] = value
            elif dump is None:
                result[api_name] = value
            else:
                result[api_name] = dump(value)

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
        for name, prop in self._get_fields():
            api_name = prop.api_name
            prop_value = value.pop(api_name, DEFAULT_VALUE)
            if prop_value is not DEFAULT_VALUE:
                if not prop.is_public():
                    raise exceptions.ValidationPropertyPrivateError(property=api_name)

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
        return orjson.dumps(
            super(JSONPacker, self).pack(obj), option=orjson.OPT_NON_STR_KEYS
        )

    def unpack(self, value):
        if isinstance(value, bytes):
            try:
                return super(JSONPacker, self).unpack(
                    orjson.loads(value),
                )
            except orjson.JSONDecodeError:
                raise exceptions.ParseBodyError()

        return super(JSONPacker, self).unpack(orjson.loads(value))


class JSONPackerIncludeNullFields(JSONPacker):
    _skip_none = False


class JSONPackerPreEncoded(JSONPacker):
    """Lets a controller hand over a body it has already serialized.

    For a document that is the same for every caller there is no reason to
    encode it again per request; a controller that keeps the encoded form can
    return it as bytes and have it written out untouched. Anything else is
    packed as usual.
    """

    def pack(self, obj: typing.Any) -> bytes:
        if isinstance(obj, bytes):
            return obj
        return super(JSONPackerPreEncoded, self).pack(obj)


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
        raise Exception("Packer can't found for content type %s " % content_type)


def set_packer(content_type, packer_class):
    packer_mapping[content_type] = packer_class
