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

The API layer in RESTAlchemy connects HTTP requests with DM models and storage.

It is responsible for:

- Routing HTTP paths and methods to controllers.
- Mapping controllers to resources backed by DM models.
- Serializing and deserializing request/response bodies.
- Applying field-level permissions and filters.
- Optionally exposing an OpenAPI specification.

---

## Core building blocks

### 1. Applications

Module: `restalchemy.api.applications`

- `WSGIApp` / `Application`:
  - Entry point for WSGI servers.
  - Takes a root route class (subclass of `routes.Route`).
  - Builds a resource map via `routes.Route.build_resource_map()` and `resources.ResourceMap.set_resource_map()`.
  - For each request:
    - Creates `RequestContext`.
    - Calls the main route's `do()` method.

- `OpenApiApplication(WSGIApp)`:
  - Extends `WSGIApp` with `openapi_engine`.
  - Used when you need to expose OpenAPI endpoints.

### 2. Routes

Module: `restalchemy.api.routes`

- `BaseRoute`:
  - Knows which controller class handles the route (`__controller__`).
  - Declares allowed methods (`__allow_methods__`).
  - Has `do()` method to process a request.

- `Route(BaseRoute)`:
  - Represents collection and resource routes.
  - Determines RA method (`FILTER/CREATE/GET/UPDATE/DELETE`) from HTTP method.
  - Delegates to appropriate controller methods (`do_collection`, `do_resource`, nested routes, actions).
  - Generates OpenAPI paths and operations when requested.

- `Action(BaseRoute)`:
  - Handles routes under `/actions/` for resource-specific operations.

- Helpers:
  - `route(route_class, resource_route=False)` — marks nested route as collection or resource route.
  - `action(action_class, invoke=False)` — marks action behaviour (`.../invoke` semantics).

### 3. Controllers

Module: `restalchemy.api.controllers`

- `Controller`:
  - Base class for controllers that work with a resource (`__resource__`).
  - Handles packing/unpacking responses via packers.
  - Implements `process_result()` to build `webob.Response`.

- `BaseResourceController` and its variants:
  - Implement `create`, `get`, `filter`, `update`, `delete` for DM models.
  - Support sorting, filtering, pagination, custom filters.

- `RoutesListController`, `RootController`:
  - Used for listing available routes (`/`, `/v1/`).

- `OpenApiSpecificationController`:
  - Serves OpenAPI specifications using the configured `openapi_engine`.

### 4. Resources

Module: `restalchemy.api.resources`

- `ResourceMap`:
  - Global mapping from DM model types to resources and from resources to URL locators.
  - Used to build `Location` headers and to resolve arbitrary URIs to resources.

- `ResourceByRAModel`:
  - Describes how a DM model is exposed via API:
    - Which fields are public.
    - How to convert model properties to API fields and back.
  - Used by packers and controllers when processing requests.

### 5. Packers

Module: `restalchemy.api.packers`

- `BaseResourcePacker`:
  - Serializes resources to simple types (`dict`, `list`, scalars).
  - Deserializes request bodies into model field values.

- `JSONPacker`, `JSONPackerIncludeNullFields`:
  - Convert between JSON and DM resource data.

- `MultipartPacker`:
  - Handles `multipart/form-data` requests (e.g. file uploads).

### 6. Contexts and permissions

- `contexts.RequestContext`:
  - Attached to each request as `req.api_context`.
  - Tracks active RA method (`FILTER/CREATE/...`).
  - Provides access to params and derived filter params.

- `field_permissions`:
  - `UniversalPermissions`, `FieldsPermissions`, `FieldsPermissionsByRole`.
  - Control which fields are visible (`HIDDEN`), read-only (`RO`) or read-write (`RW`) per method and role.

### 7. Actions

Module: `restalchemy.api.actions`

- `ActionHandler` and decorators:
  - `@actions.get`, `@actions.post`, `@actions.put`.
  - Implement method-specific behaviour for actions on resources.

Combined with `routes.Action` and `routes.action`, they provide a clean pattern for operations like `/v1/files/<id>/actions/download`.

---

## Request/response flow overview

1. **HTTP request arrives** at WSGI server.
2. `WSGIApp.__call__` is invoked:
   - Creates `RequestContext` and attaches it to `req.api_context`.
   - Calls root route `main_route(req).do()`.
3. **Route** (`Route` / `Action`) inspects `req.path_info` and `req.method`:
   - Resolves nested routes and actions.
   - Determines RA method (FILTER/CREATE/GET/UPDATE/DELETE or action).
   - Instantiates controller and delegates work.
4. **Controller**:
   - Parses filters, sorting and pagination from `RequestContext`.
   - Interacts with resources and DM models (and indirectly with storage).
   - Calls `process_result()` to convert Python objects into `webob.Response` using appropriate packer.
5. **Response** is returned to the client.

OpenAPI integration uses the same routes, controllers and resources to generate a specification, which is then served by `OpenApiSpecificationController` via `OpenApiApplication`.
