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
from restalchemy.dm import types as ra_types

DEFAULT_VALUE = object()
CONTENT_TYPE_APPLICATION_JSON = DEFAULT_CONTENT_TYPE = (
    constants.CONTENT_TYPE_APPLICATION_JSON
)

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


class BaseResourcePacker:
    _skip_none = True

    # Property types whose values this packer hands to whatever writes
    # the document out, rather than converting them itself. Empty here:
    # `pack` returns simple types, and only a packer that knows what
    # comes after it can say otherwise.
    _native_types = ()

    def __init__(self, resource_type, request):
        self._rt = resource_type
        self._req = request
        self._fields = None
        self._visible_fields = None
        self._fields_resource = None
        self._fields_by_model = {}
        self._shared = None

    def _shared_get(self, key, build):
        """What `build()` answers, kept for the requests it answers for.

        The resource hands out somewhere to keep it when every request
        that sees what this one sees would get the same answer; when it
        does not, this is a plain call.
        """
        shared = self._shared
        if shared is None:
            return build()
        value = shared.get(key)
        if value is None:
            value = build()
            shared[key] = value
        return value

    def _get_fields(self):
        """The resource fields, resolved once per packer.

        `get_fields_by_request` walks the model's properties and asks
        three predicates per field, and the answer is the same for every
        request that may see the same fields -- so it is resolved once for
        all of them, in the resource, and only per packer where it cannot
        be.

        The resource is not as fixed as the request: `routes.Action.do`
        swaps `_rt` out after building the packer, so what was resolved is
        only good for the resource it was resolved from.
        """
        if self._fields is None or self._fields_resource is not self._rt:
            self._fields_resource = self._rt
            self._shared = self._rt.request_cache(self._req) if self._rt else None
            self._visible_fields = None
            self._fields_by_model = {}
            self._fields = self._shared_get("fields", self._resolve_fields)
        return self._fields

    def _resolve_fields(self):
        return list(self._rt.get_fields_by_request(self._req))

    def _get_visible_fields(self):
        """The fields packing writes out, with their API names.

        Each carries the call that writes its value out, resolved here
        rather than reached through the field per object: `None` for a
        field whose value is already what goes on the wire.
        """
        self._get_fields()
        if self._visible_fields is None:
            # Keyed by what this packer writes out itself: two packers
            # over one resource need not agree about that, and what is
            # shared is shared by visibility, not by packer.
            self._visible_fields = self._shared_get(
                ("visible_fields", self._native_types),
                self._resolve_visible_fields,
            )
        return self._visible_fields

    def _resolve_visible_fields(self):
        native = self._native_types
        fields = []
        for name, prop in self._get_fields():
            if not prop.is_public() or self._rt._fields_permissions.is_hidden(
                name, self._req
            ):
                continue
            dump = prop.get_dump_callable()
            if dump is not None and native and type(prop.get_type()) in native:
                dump = None
            fields.append((name, prop.api_name, dump))
        return fields

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
            fields = self._shared_get(
                ("model_fields", model_class, self._native_types),
                lambda: self._resolve_fields_for_model(model_class),
            )
            self._fields_by_model[model_class] = fields
        return fields

    def _resolve_fields_for_model(self, model_class):
        defined = _class_attribute_names(model_class)
        return [
            (name, api_name, dump, name not in defined)
            for name, api_name, dump in self._get_visible_fields()
        ]

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

        values = obj_properties._values
        properties = obj_properties._properties
        result = {}
        for name, api_name, dump, own in self._get_fields_for_model(type(obj)):
            if not own:
                value = getattr(obj, name)
            elif name in values:
                # The model kept the value itself; asking it for a
                # property object would build one to read it back.
                value = values[name]
            else:
                prop = properties.get(name)
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
        if isinstance(obj, (list, types.GeneratorType)):
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
    # orjson writes these in C, and writes them the way this API says
    # they are written, so building the string here first is work the
    # document then does again. A `uuid.UUID` comes out exactly as
    # `str()` writes it; a UTC datetime comes out as RFC 3339 with `Z`,
    # which is what `OPT_UTC_Z` is for -- with one difference from what
    # this packer used to write: a timestamp landing exactly on a second
    # has no fractional part, where before it had `.000000`. Both are
    # RFC 3339. The same goes for a datetime nested inside a value, which
    # orjson has always written itself and now ends in `Z` rather than
    # `+00:00`.
    _native_types = (ra_types.UUID, ra_types.UTCDateTimeZ)

    def pack(self, obj):
        return orjson.dumps(
            super().pack(obj),
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_UTC_Z,
        )

    def unpack(self, value):
        if isinstance(value, bytes):
            try:
                return super().unpack(
                    orjson.loads(value),
                )
            except orjson.JSONDecodeError:
                raise exceptions.ParseBodyError()

        return super().unpack(orjson.loads(value))


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
        raise Exception(  # noqa: TRY002
            f"Packer can't found for content type {content_type} "
        )


def set_packer(content_type, packer_class):
    packer_mapping[content_type] = packer_class
