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

# Nested resources und Actions

Dieses How-to erklärt, wie man:

- verschachtelte Ressourcen implementiert (z. B. `/foos/<uuid>/bars/`),
- Actions auf Ressourcen implementiert (z. B. `/v1/files/<id>/actions/download`).

Es baut auf dem Basic-CRUD-Beispiel auf und nutzt Ideen aus `examples/restapi_foo_bar_service.py` und `examples/openapi_app.py`.

---

## 1. Verschachtelte Ressourcen

Verschachtelte Ressourcen bilden hierarchische Beziehungen ab, z. B.:

- Elternelement: `FooModel` unter `/v1/foos/<uuid>`
- Verschachtelte Collection: `BarModel` unter `/v1/foos/<uuid>/bars/`

### 1.1 DM-Modelle

Wie im Basic-CRUD-Beispiel:

```python
class FooModel(models.ModelWithUUID):
    foo_field1 = properties.property(types.Integer(), required=True)
    foo_field2 = properties.property(types.String(), default="foo_str")


class BarModel(models.ModelWithUUID):
    bar_field1 = properties.property(types.String(min_length=1, max_length=10))
    foo = relationships.relationship(FooModel)
```

### 1.2 Verschachtelter Controller

Sie können `BaseNestedResourceController` verwenden oder die Logik explizit in einem eigenen Controller implementieren.

```python
class BarController1(controllers.Controller):
    """Handler für /v1/foos/<uuid>/bars/."""

    __resource__ = resources.ResourceByRAModel(BarModel, process_filters=True)

    def create(self, bar_field1, parent_resource):
        bar = BarModel(bar_field1=bar_field1, foo=parent_resource)
        bar_storage[str(bar.get_id())] = bar
        return bar

    def filter(self, filters, parent_resource, order_by=None):
        # Einfache Filterung: nur Bars für das gegebene Foo
        return [
            bar for bar in bar_storage.values() if bar.foo == parent_resource
        ]
```

Stattdessen kann auch `BaseNestedResourceController` verwendet werden, um die Behandlung von `parent_resource` zu kapseln.

### 1.3 Verschachtelte Route

```python
class BarRoute1(routes.Route):
    __controller__ = BarController1
    __allow_methods__ = [routes.CREATE, routes.FILTER]


class FooRoute(routes.Route):
    __controller__ = FooController
    __allow_methods__ = [routes.FILTER, routes.CREATE, routes.GET]

    bars = routes.route(BarRoute1, resource_route=True)
```

- `resource_route=True` signalisiert, dass `BarRoute1` unterhalb einer konkreten Elternressource (`FooModel` Instanz) arbeitet.
- Für `/v1/foos/<foo_uuid>/bars/` löst RA das übergeordnete `FooModel` aus der URL auf und übergibt es als `parent_resource`.

---

## 2. Actions auf Ressourcen

Actions repräsentieren Operationen, die nicht reine CRUD-Operationen auf der Hauptressource sind, z. B.:

- `/v1/files/<id>/actions/download` — Datei-Download.
- `/v1/objects/<id>/actions/some_business_operation`.

### 2.1 Definition einer Action mit ActionHandler

Modul: `restalchemy.api.actions`

```python
from restalchemy.api import actions, constants
from restalchemy.api import controllers, resources


class FileModel(models.ModelWithUUID):
    name = properties.property(types.String(), required=True)


class FilesController(controllers.Controller):
    __resource__ = resources.ResourceByRAModel(
        model_class=FileModel,
        process_filters=True,
        convert_underscore=False,
    )

    @actions.get
    def download(self, resource, **kwargs):
        # resource repräsentiert hier z. B. eine Datei-Beschreibung
        data = resource.download_file()
        headers = {
            "Content-Type": constants.CONTENT_TYPE_OCTET_STREAM,
            "Content-Disposition": f'attachment; filename="{resource.name}"',
        }
        return data, 200, headers
```

- `@actions.get` wrappt die Methode in einen `ActionHandler`.
- Der Controller erhält `self` als `controller` und `resource` als aktuelle DM-Instanz.
- Über `controller.process_result()` (indirekt via `ActionHandler.do_*`) wird die Response erzeugt.

### 2.2 Action-Route definieren

```python
from restalchemy.api import routes


class FileDownloadAction(routes.Action):
    """Handler für /v1/files/<id>/actions/download."""

    __controller__ = FilesController
```

Anschließend wird die Action an die Ressource gehängt:

```python
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
```

- `routes.action(FileDownloadAction, invoke=True)` bedeutet:
  - Die Action ist unter `/v1/files/<id>/actions/download/invoke` erreichbar.
  - HTTP-Methoden `GET/POST/PUT` werden auf `do_get/do_post/do_put` im `ActionHandler` gemappt.

### 2.3 Request-/Response-Flow für Actions

Für eine URL wie `/v1/files/<id>/actions/download/invoke`:

1. `Route.do()` erkennt das Segment `actions` im Pfad.
2. Die Ressource wird über `<id>` mit Hilfe des Controllers geladen.
3. Die Action (`download`) wird ermittelt.
4. `FileDownloadAction` wird mit dem Request instanziiert.
5. `Action.do(resource=resource, **kwargs)` wird aufgerufen.
6. `Action` nutzt `ActionHandler`, um die passende `do_*`-Methode auszuführen.

---

## 3. Kombination von verschachtelten Ressourcen und Actions

Actions lassen sich auch auf verschachtelten Ressourcen verwenden, z. B.:

- `/v1/foos/<foo_id>/bars/<bar_id>/actions/archive`.

In diesem Fall:

- beschreibt der Routenbaum verschachtelte Routen bis hin zur `BarRoute`;
- eine `Action` unterhalb von `BarRoute` arbeitet auf der verschachtelten `BarModel`-Instanz.

Das Muster ist identisch zu Top-Level-Ressourcen; lediglich der Pfad wird länger.

---

## Zusammenfassung

- Verschachtelte Ressourcen werden über verschachtelte `Route`-Klassen und `resource_route=True` ausgedrückt.
- Controller können `parent_resource` (oder `BaseNestedResourceController`) nutzen, um Logik relativ zu einer Elterninstanz zu implementieren.
- Actions werden über `ActionHandler`-Dekoratoren und `routes.Action`/`routes.action` implementiert und erlauben eine saubere Modellierung von Nicht-CRUD-Operationen auf Ressourcen.
