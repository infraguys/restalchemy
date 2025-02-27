# Copyright 2022 Eugene Frolov <eugene@frolov.net.ru>
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

from restalchemy.api import constants as ra_const
from restalchemy.common import status

OPENAPI_SPECIFICATION_3_0_3 = "3.0.3"

API_VERSION_V1 = "v1"

ERROR_SCHEMA = {
    "title": "error",
    "description": "Error occurred while processing request",
    "type": "object",
    "required": [
        "status",
        "json",
    ],
    "properties": {
        "status": {
            "type": "integer",
            "description": "The HTTP status code",
            "minimum": 400,
            "exclusiveMaximum": True,
            "example": 503,
        },
        "json": {
            "type": "object",
            "description": "Detail error map",
            "required": [
                "code",
                "type",
                "message",
            ],
            "properties": {
                "code": {
                    "type": "integer",
                    "description": "The HTTP status code",
                    "minimum": 400,
                    "exclusiveMaximum": True,
                    "example": 503,
                },
                "type": {
                    "type": "string",
                    "description": "Error class name",
                    "example": "OSError",
                },
                "message": {
                    "type": "string",
                    "description": "Error message",
                    "example": "A human-readable explanation of problem",
                },
            },
        },
    },
    "example": {
        "code": 400,
        "json": {
            "code": 400,
            "type": "ValidationErrorException",
            "message": "Validation error occurred.",
        },
    },
}

ERROR_RESPONSE = {
    "description": "Error response.",
    "content": {
        ra_const.CONTENT_TYPE_APPLICATION_JSON: {
            "schema": {"$ref": "#/components/schemas/Error"}
        }
    },
}

DEFAULT_RESPONSE = {"$ref": "#/components/responses/Error"}

OPENAPI_DELETE_RESPONSE = {
    status.HTTP_204_NO_CONTENT: {
        "description": "Delete entity",
    },
    "default": DEFAULT_RESPONSE,
}

OPENAPI_FILTER_RESPONSE = {
    status.HTTP_200_OK: {
        "description": "Get nested urls",
        "content": {
            ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                "schema": {"type": "array", "items": {"type": "string"}}
            }
        },
    },
    "default": DEFAULT_RESPONSE,
}

OPENAPI_DEFAULT_RESPONSE = {
    status.HTTP_200_OK: {
        "description": "Get nested urls",
        "content": {ra_const.CONTENT_TYPE_APPLICATION_JSON: {"schema": {}}},
    },
    "default": DEFAULT_RESPONSE,
}


def build_openapi_create_response(ref_name):
    return {
        status.HTTP_201_CREATED: {
            "description": ref_name,
            "content": {
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                    "schema": {
                        "$ref": "#/components/schemas/{}".format(ref_name)
                    }
                }
            },
        },
        "default": DEFAULT_RESPONSE,
    }


def build_openapi_get_update_response(ref_name):
    return {
        status.HTTP_200_OK: {
            "description": ref_name,
            "content": {
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                    "schema": {
                        "$ref": "#/components/schemas/{}".format(ref_name)
                    }
                }
            },
        },
        "default": DEFAULT_RESPONSE,
    }


def build_openapi_list_model_response(ref_name):
    return {
        status.HTTP_200_OK: {
            "description": ref_name,
            "content": {
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                    "schema": {
                        "type": "array",
                        "items": {
                            "$ref": "#/components/schemas/{}".format(ref_name)
                        },
                    }
                }
            },
        },
        "default": DEFAULT_RESPONSE,
    }


def build_openapi_delete_response(ref_name):
    return {
        status.HTTP_204_NO_CONTENT: {
            "description": ref_name,
        },
        "default": DEFAULT_RESPONSE,
    }


def build_openapi_object_response(
    properties,
    code=200,
    description="",
    content_type=ra_const.CONTENT_TYPE_APPLICATION_JSON,
):
    """

    properties - dict as needed in openapi
    https://swagger.io/docs/specification/describing-responses/

    Ex:
    {
    "id": {"type": "integer", "description": "The user ID"}
    "username": {"type": "string", "description": "The user name"}
    }

    """
    return {
        code: {
            "description": description,
            "content": {
                content_type: {
                    "schema": {"type": "object", "properties": properties}
                }
            },
        },
        "default": DEFAULT_RESPONSE,
    }


def build_openapi_response_octet_stream(description="Returns binary file"):
    return {
        status.HTTP_200_OK: {
            "description": description,
            "content": {
                ra_const.CONTENT_TYPE_OCTET_STREAM: {
                    "schema": {"format": "binary", "type": "string"}
                }
            },
        },
    }


def build_openapi_user_response(
    code=status.HTTP_200_OK, description="", **kwargs
):
    """

    properties - dict as needed in openapi
    https://swagger.io/docs/specification/describing-responses/

    Ex:
    {
    "id": {"type": "integer", "description": "The user ID"}
    "username": {"type": "string", "description": "The user name"}
    }

    """
    if not kwargs:
        raise ValueError("**kwargs are required.")
    return {
        code: {
            "description": description,
            "content": {
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {"schema": kwargs}
            },
        },
        "default": DEFAULT_RESPONSE,
    }


def build_openapi_req_body(description, content_type, schema):
    return {
        "description": description,
        "required": True,
        "content": {content_type: {"schema": schema}},
    }


def build_openapi_req_body_multipart(description, properties):

    props = {}
    # See openapi types, examples:
    #  {"format": "binary", "type": "string"} - for files
    #  {"format": "uuid", "type": "string"} - for uuids
    for name, pval in properties.items():
        props[name] = pval

    return build_openapi_req_body(
        description=description,
        content_type=ra_const.CONTENT_TYPE_MULTIPART,
        schema={"properties": props},
    )


def build_openapi_json_req_body(model_name):
    return build_openapi_req_body(
        model_name,
        ra_const.CONTENT_TYPE_APPLICATION_JSON,
        {"$ref": f"#/components/schemas/{model_name}"},
    )


def build_openapi_parameter(
    name,
    description="",
    required=True,
    openapi_type="string",
    param_type="path",
    schema=None,
):
    param = {
        "name": name,
        "description": description,
        "in": param_type,
        "schema": schema or {"type": openapi_type},
    }
    if param_type == "path" and required is not None:
        param["required"] = required
    return param
