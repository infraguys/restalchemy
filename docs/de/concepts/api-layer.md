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

# API layer

Die API-Schicht in RESTAlchemy verbindet HTTP-Anfragen mit DM-Modellen und der Storage-Schicht.

Sie ist verantwortlich für:

- Routing von HTTP-Pfaden und -Methoden zu Controllern.
- Abbildung von Controllern auf Ressourcen, die auf DM-Modellen basieren.
- Serialisierung und Deserialisierung von Request-/Response-Bodies.
- Anwendung von feldbasierten Berechtigungen und Filtern.
- Optionale Bereitstellung einer OpenAPI-Spezifikation.

---

## Zentrale Bausteine

### 1. Applications

Modul: `restalchemy.api.applications`

- `WSGIApp` / `Application`:
  - Einstiegspunkt für WSGI-Server.
  - Nimmt eine Root-Route-Klasse (Subklasse von `routes.Route`) entgegen.
  - Baut die Resource-Map über `routes.Route.build_resource_map()` und `resources.ResourceMap.set_resource_map()`.
  - Für jede Anfrage:
    - Erstellt einen `RequestContext`.
    - Ruft die `do()`-Methode der Root-Route auf.

- `OpenApiApplication(WSGIApp)`:
  - Erweitert `WSGIApp` um ein `openapi_engine`-Attribut.
  - Wird verwendet, wenn das API eine OpenAPI-Spezifikation ausliefern soll.

### 2. Routes

Modul: `restalchemy.api.routes`

- `BaseRoute`:
  - Kennt die zuständige Controller-Klasse (`__controller__`).
  - Deklariert erlaubte Methoden (`__allow_methods__`).
  - Definiert eine `do()`-Methode zur Verarbeitung der Anfrage.

- `Route(BaseRoute)`:
  - Repräsentiert Collection- und Resource-Routen.
  - Leitet aus dem HTTP-Verb die RA-Methode ab (`FILTER/CREATE/GET/UPDATE/DELETE`).
  - Delegiert an Controller-Methoden (`do_collection`, `do_resource`, verschachtelte Routen, Actions).
  - Kann OpenAPI-Pfade und Operationen generieren.

- `Action(BaseRoute)`:
  - Behandelt Routen unter `/actions/` für ressourcenspezifische Operationen.

- Hilfsfunktionen:
  - `route(route_class, resource_route=False)` — markiert eine verschachtelte Route als Collection- oder Resource-Route.
  - `action(action_class, invoke=False)` — steuert das Action-Verhalten (`.../invoke`).

### 3. Controller

Modul: `restalchemy.api.controllers`

- `Controller`:
  - Basisklasse für Controller, die mit einer Resource (`__resource__`) arbeiten.
  - Steuert die Serialisierung/Deserialisierung mittels Packer (`packers`).
  - Implementiert `process_result()`, um eine `webob.Response` zu erzeugen.

- `BaseResourceController` und Varianten:
  - Implementieren `create`, `get`, `filter`, `update`, `delete` für DM-Modelle.
  - Unterstützen Sortierung, Filter, Paginierung und benutzerdefinierte Filterlogik.

- `RoutesListController`, `RootController`:
  - Dienen dazu, verfügbare Routen aufzulisten (`/`, `/v1/`).

- `OpenApiSpecificationController`:
  - Stellt OpenAPI-Spezifikationen mit Hilfe des konfigurierten `openapi_engine` bereit.

### 4. Resources

Modul: `restalchemy.api.resources`

- `ResourceMap`:
  - Globale Abbildung von DM-Modelltypen auf Ressourcen und von Ressourcen auf URL-Lokatoren.
  - Wird genutzt, um `Location`-Header zu erzeugen und beliebige URIs auf Ressourcen aufzulösen.

- `ResourceByRAModel`:
  - Beschreibt, wie ein DM-Modell im API dargestellt wird:
    - Welche Felder öffentlich sind.
    - Wie Modell-Properties in API-Felder (und zurück) konvertiert werden.
  - Wird von Packern und Controllern bei der Request-Verarbeitung verwendet.

### 5. Packer

Modul: `restalchemy.api.packers`

- `BaseResourcePacker`:
  - Serialisiert Ressourcen in einfache Typen (`dict`, `list`, Skalare).
  - Deserialisiert Request-Bodies in Modellwerte.

- `JSONPacker`, `JSONPackerIncludeNullFields`:
  - Konvertieren zwischen JSON und DM-Ressourcendaten.

- `MultipartPacker`:
  - Behandelt `multipart/form-data` (z.B. Datei-Uploads).

### 6. Contexts und Feldberechtigungen

- `contexts.RequestContext`:
  - Wird als `req.api_context` an die Anfrage gehängt.
  - Hält die aktuell aktive RA-Methode (`FILTER/CREATE/...`).
  - Bietet Zugriff auf Request-Parameter und abgeleitete Filter-Parameter.

- Modul `field_permissions`:
  - `UniversalPermissions`, `FieldsPermissions`, `FieldsPermissionsByRole`.
  - Steuern, ob Felder verborgen (`HIDDEN`), read-only (`RO`) oder read-write (`RW`) sind — abhängig von Methode und Rolle.

### 7. Actions

Modul: `restalchemy.api.actions`

- `ActionHandler` und Dekoratoren:
  - `@actions.get`, `@actions.post`, `@actions.put`.
  - Implementieren methodenspezifisches Verhalten für Actions auf Ressourcen.

In Kombination mit `routes.Action` und `routes.action` entsteht so ein klares Muster für Operationen wie `/v1/files/<id>/actions/download`.

---

## Überblick über den Request-/Response-Flow

1. **HTTP-Anfrage trifft ein** beim WSGI-Server.
2. `WSGIApp.__call__` wird aufgerufen:
   - Erstellt `RequestContext` und hängt ihn als `req.api_context` an.
   - Ruft `main_route(req).do()` der Root-Route auf.
3. **Route** (`Route` / `Action`) inspiziert `req.path_info` und `req.method`:
   - Löst verschachtelte Routen und Actions auf.
   - Bestimmt die RA-Methode (FILTER/CREATE/GET/UPDATE/DELETE oder Action).
   - Erzeugt den Controller und übergibt die Steuerung.
4. **Controller**:
   - Liest Filter, Sortierung und Paginierung aus dem `RequestContext`.
   - Interagiert mit Ressourcen und DM-Modellen (und indirekt mit der Storage-Schicht).
   - Ruft `process_result()` auf, um Python-Objekte mit Hilfe des passenden Packers in eine `webob.Response` zu konvertieren.
5. **Response** wird an den Client zurückgeliefert.

Die OpenAPI-Integration verwendet dieselben Routen, Controller und Ressourcen, um eine Spezifikation zu erzeugen, die dann von `OpenApiSpecificationController` über `OpenApiApplication` ausgeliefert wird.
