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
from restalchemy.common import exceptions as exc
from restalchemy.common import status

OPENAPI_SPECIFICATION_3_0_3 = "3.0.3"

API_VERSION_V1 = "v1"

OPENAPI_DELETE_RESPONSE = {
    status.HTTP_204_NO_CONTENT: {
        "description": "",
        "content": {
            ra_const.CONTENT_TYPE_APPLICATION_JSON: {
            }
        }
    },
    exc.NotFoundError.code: {
        "description": exc.NotFoundError.message,
    }
}

OPENAPI_FILTER_RESPONSE = {
    status.HTTP_200_OK: {
        "description": "Get nested urls",
        "content": {
            ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
    },
    exc.IncorrectRouteAttribute.code: {
        "description": exc.IncorrectRouteAttribute.message,
    },
}

OPENAPI_DEFAULT_RESPONSE = {
    status.HTTP_200_OK: {
        "description": "Get nested urls",
        "content": {
            ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                "schema": {}
            }
        }
    }
}


def build_openapi_create_response(ref_name):
    return {
        status.HTTP_201_CREATED: {
            "description": ref_name,
            "content": {
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                    "schema": {
                        "$ref": "#/components/schemas/{}".format(
                            ref_name)
                    }
                }
            }
        },
        exc.ValidationErrorException.code: {
            "description": exc.ValidationErrorException.message,
        },
        exc.NotFoundError.code: {
            "description": exc.NotFoundError.message % {"path": ""},
        }
    }


def build_openapi_get_update_response(ref_name):
    return {
        status.HTTP_200_OK: {
            "description": ref_name,
            "content": {
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                    "schema": {
                        "$ref": "#/components/schemas/{}".format(
                            ref_name)
                    }
                }
            }
        },
        exc.ValidationErrorException.code: {
            "description": exc.ValidationErrorException.message,
        },
        exc.NotFoundError.code: {
            "description": exc.NotFoundError.message % {"path": ""},
        }
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
                            "$ref": "#/components/schemas/{}".format(
                                ref_name)
                        }
                    }
                }
            }
        },
        exc.ValidationErrorException.code: {
            "description": exc.ValidationErrorException.message,
        },
        exc.NotFoundError.code: {
            "description": exc.NotFoundError.message % {"path": ""},
        }
    }


def build_openapi_object_response(properties,
                                  code=200,
                                  description="",
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
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                    "schema": {
                        "type": "object",
                        "properties": properties
                    }
                }
            }
        },
        exc.ValidationErrorException.code: {
            "description": exc.ValidationErrorException.message,
        },
        exc.NotFoundError.code: {
            "description": exc.NotFoundError.message % {"path": ""},
        }
    }


def build_openapi_user_response(code=status.HTTP_200_OK,
                                description="",
                                **kwargs):
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
                ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                    "schema": kwargs
                }
            }
        },
        exc.ValidationErrorException.code: {
            "description": exc.ValidationErrorException.message,
        },
        exc.NotFoundError.code: {
            "description": exc.NotFoundError.message % {"path": ""},
        }
    }


def build_openapi_json_req_body(model_name):
    return {
        "description": model_name,
        "required": True,
        "content": {
            ra_const.CONTENT_TYPE_APPLICATION_JSON: {
                "schema": {
                    "$ref": "#/components/schemas/{}".format(
                        model_name)
                }
            }
        }
    }


def build_openapi_parameter(name,
                            description="",
                            required=True,
                            openapi_type='string',
                            param_type="path",
                            schema=None):
    param = {
        'name': name,
        'description': description,
        'in': param_type,
        'schema': schema or {'type': openapi_type},
    }
    if param_type == "path" and required is not None:
        param["required"] = required
    return param
