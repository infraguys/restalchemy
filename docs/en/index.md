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

# RESTAlchemy

RESTAlchemy is a Python toolkit for building HTTP REST APIs on top of a flexible data model and storage abstraction.

It combines:

- A **Data Model (DM)** layer for defining domain models and validation.
- A **Storage** layer for persisting models (e.g. SQL databases).
- An **API** layer for exposing models as RESTful HTTP resources.
- Optional **OpenAPI** support for discoverable, documented APIs.

All documentation is available in four languages:

- English (`docs/en`)
- Russian (`docs/ru`)
- German (`docs/de`)
- Chinese (`docs/zh`)

The structure of files and sections is identical across all languages.

---

## Core concepts

### Data Model (DM)

DM is responsible for:

- Declaring models and fields.
- Validating values and types.
- Expressing relationships between models.

You define Python classes that inherit from DM base classes (for example, `ModelWithUUID`) and use `properties` and `types` to describe fields.

### Storage

The storage layer provides:

- An abstraction over SQL engines (MySQL, PostgreSQL, etc.).
- Sessions and transactions.
- Query helpers and filtering.

You can start without any persistent storage (in-memory only) and later plug in SQL storage.

### API

The API layer provides:

- Controllers that implement business logic.
- Resources that describe how DM models are exposed via HTTP.
- Routes that map URLs and HTTP methods to controllers.
- Middlewares and WSGI applications.

You can start from a very small in-memory service and gradually adopt DM and Storage for production use.

### OpenAPI (optional)

OpenAPI integration allows you to:

- Auto-generate OpenAPI specifications from controllers and routes.
- Serve OpenAPI documents from your API.
- Integrate with tools like Swagger UI or client generators.

---

## When should you use RESTAlchemy?

Use RESTAlchemy when:

- **You want** a clear separation between:
  - your domain models (DM),
  - storage implementation details,
  - and HTTP API,  
  but you do not want a full-blown monolithic framework.
- **You need** a strongly typed, validated data model with reusable properties.
- **You want** to expose your models as REST resources with minimal boilerplate.
- **You care** about migrations and database evolution.

---

## Quick navigation

Recommended reading order if you are new to RESTAlchemy:

1. [Installation](installation.md)
2. [Getting started](getting-started.md) — build a small in-memory REST service.
3. Concepts:
   - [Data model](concepts/data-model.md)
   - [API layer](concepts/api-layer.md)
   - [Storage layer](concepts/storage-layer.md)
4. How-to guides:
   - Basic CRUD
   - Filtering, sorting, pagination
   - Relationships between models
5. Reference:
   - `restalchemy.api.*`
   - `restalchemy.dm.*`
   - `restalchemy.storage.*`

You should be able to build a working service after reading only:

- `installation.md`
- `getting-started.md`

---

## Examples

Real code examples live in the `examples/` directory of the repository. In particular:

- `examples/restapi_foo_bar_service.py`  
  A simple REST API service built with in-memory storage.
- `examples/dm_mysql_storage.py`  
  Data model + MySQL storage example.
- `examples/openapi_app.py`  
  Example of an API with OpenAPI specification generation.

The rest of the documentation will reference these examples where relevant.
