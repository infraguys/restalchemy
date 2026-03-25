<!--
Copyright 2025 Genesis Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# OpenAPI 集成

本指南展示如何在 RESTAlchemy API 中集成 OpenAPI。

我们将：

- 创建带 OpenAPI 路由的 API。
- 使用 `OpenApiApplication` 和 `OpenApiSpecificationRoute`。
- 通过 OpenAPI schema 注解控制器方法。
- 通过 HTTP 获取 OpenAPI 规范。

示例基于 `examples/openapi_app.py`。

---

## 1. DM 模型

```python
from restalchemy.dm import models, properties, types


class FileModel(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)
```

---

## 2. 带 OpenAPI 注解的控制器

模块：`restalchemy.openapi.utils` 与 `restalchemy.openapi.constants` 用于描述 schema。

```python
from restalchemy.api import actions, constants, controllers, resources
from restalchemy.openapi import constants as oa_c
from restalchemy.openapi import engines as openapi_engines
from restalchemy.openapi import structures as openapi_structures
from restalchemy.openapi import utils as oa_utils


class FilesController(controllers.Controller):
    """Controller for /v1/files/[<id>] endpoint."""

    __resource__ = resources.ResourceByRAModel(
        model_class=FileModel,
        process_filters=True,
        convert_underscore=False,
    )

    def create(self, **kwargs):
        # Implement file upload logic here
        pass

    create.openapi_schema = oa_utils.Schema(
        summary="Upload file",
        parameters=(),
        responses=oa_c.build_openapi_create_response(
            "%s_Create" % __resource__.get_model().__name__
        ),
        request_body=oa_c.build_openapi_req_body_multipart(
            description="Upload file to docs set",
            properties={"file": {"format": "binary", "type": "string"}},
        ),
    )

    @oa_utils.extend_schema(
        summary="Download file",
        parameters=(),
        responses=oa_c.build_openapi_response_octet_stream(),
    )
    @actions.get
    def download(self, resource, **kwargs):
        data = resource.download_file()
        headers = {
            "Content-Type": constants.CONTENT_TYPE_OCTET_STREAM,
            "Content-Disposition": f'attachment; filename="{resource.name}"',
        }
        return data, 200, headers

    download.openapi_schema = oa_utils.Schema(
        summary="Download file",
        parameters=(),
        responses=oa_c.build_openapi_response_octet_stream(),
    )
```

要点：

- 绑定在控制器方法上的 `oa_utils.Schema` 用于描述：
  - `summary`、`parameters`、`responses`、`request_body`、`tags`。
- `@oa_utils.extend_schema` 是用于 actions 的装饰器形式。
- 如果你不提供 schema，RA 会基于资源与 DM 类型生成合理的默认值。

---

## 3. 路由与 OpenAPI 规范路由

```python
from restalchemy.api import routes


class FileDownloadAction(routes.Action):
    """Handler for /v1/files/<id>/actions/download endpoint."""

    __controller__ = FilesController


class FilesRoute(routes.Route):
    """Handler for /v1/files/<id> endpoint."""

    __controller__ = FilesController
    __allow_methods__ = [
        routes.CREATE,
        routes.DELETE,
        routes.FILTER,
        routes.GET,
        routes.UPDATE,
    ]

    download = routes.action(FileDownloadAction, invoke=True)


class ApiEndpointController(controllers.RoutesListController):
    """Controller for /v1/ endpoint."""

    __TARGET_PATH__ = "/v1/"


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint."""

    __controller__ = ApiEndpointController
    __allow_methods__ = [routes.FILTER, routes.GET]

    specifications = routes.action(routes.OpenApiSpecificationRoute)
    files = routes.route(FilesRoute)


class UserApiApp(routes.RootRoute):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


setattr(UserApiApp, "v1", routes.route(ApiEndpointRoute))
```

- `OpenApiSpecificationRoute` 是内置路由，用于暴露 OpenAPI 规范。
- `ApiEndpointRoute.specifications` 将其挂载到 `/v1/specifications/`。

---

## 4. OpenAPI engine 与应用

```python
from restalchemy.api import applications, middlewares


def get_openapi_engine():
    openapi_engine = openapi_engines.OpenApiEngine(
        info=openapi_structures.OpenApiInfo(),
        paths=openapi_structures.OpenApiPaths(),
        components=openapi_structures.OpenApiComponents(),
    )
    return openapi_engine


def get_user_api_application():
    return UserApiApp


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.OpenApiApplication(
            route_class=get_user_api_application(),
            openapi_engine=get_openapi_engine(),
        ),
        [],
    )
```

- `OpenApiApplication` 在 `WSGIApp` 基础上增加 `openapi_engine` 属性。
- `OpenApiSpecificationController` 使用该 engine 构建并返回规范。

---

## 5. 获取 OpenAPI 规范

启动应用后，你可以通过如下方式获取规范：

```bash
curl http://127.0.0.1:8000/v1/specifications/3.0.3
```

- 路径中的版本号（`3.0.3`）对应请求的 OpenAPI 版本。
- 响应为 JSON 格式的 OpenAPI 文档。

你可以将该 URL 用于 Swagger UI 或客户端代码生成器。

---

## 小结

- 使用 `OpenApiApplication` 与 `OpenApiSpecificationRoute` 暴露 OpenAPI。
- 需要精细控制时，为控制器方法添加 `oa_utils.Schema` 或使用 `@extend_schema`。
- 否则可以依赖 RA 基于资源与 DM 类型推导出的默认值。
