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

# Интеграция с OpenAPI

В этом руководстве показано, как интегрировать OpenAPI с RESTAlchemy API.

Мы:

- Создадим API с OpenAPI-роутами.
- Подключим `OpenApiApplication` и `OpenApiSpecificationRoute`.
- Аннотируем контроллеры схемами OpenAPI.
- Получим OpenAPI-спецификацию.

Пример основан на `examples/openapi_app.py`.

---

## 1. DM-модель

```python
from restalchemy.dm import models, properties, types


class FileModel(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)
```

---

## 2. Контроллер с OpenAPI-аннотациями

Модули: `restalchemy.openapi.utils` и `restalchemy.openapi.constants` используются для описания схем.

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

Ключевые моменты:

- Объекты `oa_utils.Schema`, прикреплённые к методам контроллера, описывают:
  - `summary`, `parameters`, `responses`, `request_body`, `tags`.
- `@oa_utils.extend_schema` — вариант через декоратор для actions.
- Если схемы не заданы, RA сгенерирует разумные значения по умолчанию на основе ресурсов и DM-типов.

---

## 3. Роуты и роут спецификации OpenAPI

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

- `OpenApiSpecificationRoute` — встроенный роут, который отдаёт OpenAPI-спеки.
- `ApiEndpointRoute.specifications` подключает его по пути `/v1/specifications/`.

---

## 4. OpenAPI engine и приложение

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

- `OpenApiApplication` расширяет `WSGIApp` свойством `openapi_engine`.
- `OpenApiSpecificationController` использует этот engine для построения спеки.

---

## 5. Получение OpenAPI спеки

После запуска приложения вы можете получить спеку:

```bash
curl http://127.0.0.1:8000/v1/specifications/3.0.3
```

- Версия в пути (`3.0.3`) соответствует версии OpenAPI, которую вы запрашиваете.
- В ответе возвращается JSON-документ OpenAPI.

Этот URL можно подключить к Swagger UI или генераторам клиентов.

---

## Резюме

- Используйте `OpenApiApplication` и `OpenApiSpecificationRoute`, чтобы отдавать OpenAPI.
- Аннотируйте методы контроллеров через `oa_utils.Schema` или `@extend_schema`, когда нужен точный контроль.
- Иначе можно опираться на defaults RA, полученные из ресурсов и DM-типов.
