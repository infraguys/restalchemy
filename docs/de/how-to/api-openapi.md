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

# OpenAPI-Integration

Dieses How-to zeigt, wie man OpenAPI in RESTAlchemy-APIs integriert.

Wir werden:

- Eine API mit OpenAPI-Routen erstellen.
- `OpenApiApplication` und `OpenApiSpecificationRoute` verwenden.
- Controller mit OpenAPI-Schemas annotieren.
- Die OpenAPI-Spezifikation abrufen.

Das Beispiel basiert auf `examples/openapi_app.py`.

---

## 1. DM-Modell

```python
from restalchemy.dm import models, properties, types


class FileModel(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)
```

---

## 2. Controller mit OpenAPI-Annotationen

Module: `restalchemy.openapi.utils` und `restalchemy.openapi.constants` werden für Schemas verwendet.

```python
from restalchemy.api import actions, constants, controllers, resources
from restalchemy.openapi import constants as oa_c
from restalchemy.openapi import engines as openapi_engines
from restalchemy.openapi import structures as openapi_structures
from restalchemy.openapi import utils as oa_utils


class FilesController(controllers.Controller):
    """Controller für /v1/files/[<id>] Endpunkt."""

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

Wichtige Punkte:

- `oa_utils.Schema`-Objekte, die an Controller-Methoden gehängt werden, beschreiben:
  - `summary`, `parameters`, `responses`, `request_body`, `tags`.
- `@oa_utils.extend_schema` ist eine dekoratorbasierte Variante für Actions.
- Wenn Sie keine Schemas angeben, generiert RA sinnvolle Defaults basierend auf Resources und DM-Typen.

---

## 3. Routen und OpenAPI-Spezifikations-Route

```python
from restalchemy.api import routes


class FileDownloadAction(routes.Action):
    """Handler für /v1/files/<id>/actions/download Endpunkt."""

    __controller__ = FilesController


class FilesRoute(routes.Route):
    """Handler für /v1/files/<id> Endpunkt."""

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
    """Controller für /v1/ Endpunkt."""

    __TARGET_PATH__ = "/v1/"


class ApiEndpointRoute(routes.Route):
    """Handler für /v1/ Endpunkt."""

    __controller__ = ApiEndpointController
    __allow_methods__ = [routes.FILTER, routes.GET]

    specifications = routes.action(routes.OpenApiSpecificationRoute)
    files = routes.route(FilesRoute)


class UserApiApp(routes.RootRoute):
    __controller__ = controllers.RootController
    __allow_methods__ = [routes.FILTER]


setattr(UserApiApp, "v1", routes.route(ApiEndpointRoute))
```

- `OpenApiSpecificationRoute` ist eine eingebaute Route, die OpenAPI-Specs bereitstellt.
- `ApiEndpointRoute.specifications` hängt sie unter `/v1/specifications/` ein.

---

## 4. OpenAPI-Engine und Application

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

- `OpenApiApplication` erweitert `WSGIApp` um die Eigenschaft `openapi_engine`.
- `OpenApiSpecificationController` verwendet diese Engine, um die Spec zu bauen.

---

## 5. OpenAPI-Spec abrufen

Nachdem die Anwendung gestartet ist, können Sie die Spec abrufen:

```bash
curl http://127.0.0.1:8000/v1/specifications/3.0.3
```

- Die Pfadversion (`3.0.3`) entspricht der angefragten OpenAPI-Version.
- Die Antwort ist ein JSON-OpenAPI-Dokument.

Sie können diese URL z. B. in Swagger UI oder Code-Generatoren verwenden.

---

## Zusammenfassung

- Verwenden Sie `OpenApiApplication` und `OpenApiSpecificationRoute`, um OpenAPI bereitzustellen.
- Annotieren Sie Controller-Methoden mit `oa_utils.Schema` oder `@extend_schema`, wenn Sie feine Kontrolle benötigen.
- Andernfalls verlassen Sie sich auf RAs Defaults, die aus Resources und DM-Typen abgeleitet werden.
