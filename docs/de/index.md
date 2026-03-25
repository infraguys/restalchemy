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

RESTAlchemy ist ein Python-Toolkit zum Aufbau von HTTP-REST-APIs auf Basis eines flexiblen Datenmodells und einer Storage-Abstraktion.

Es kombiniert:

- Eine **Data Model (DM)**-Schicht für Domänenmodelle und Validierung.
- Eine **Storage**-Schicht für Persistenz (z. B. SQL-Datenbanken).
- Eine **API**-Schicht zur Veröffentlichung der Modelle als REST-Ressourcen.
- Optionale **OpenAPI**-Unterstützung für dokumentierte APIs.

Die Dokumentation ist in vier Sprachen verfügbar:

- Englisch (`docs/en`)
- Russisch (`docs/ru`)
- Deutsch (`docs/de`)
- Chinesisch (`docs/zh`)

Die Struktur der Dateien und Abschnitte ist in allen Sprachen identisch.

---

## Zentrale Konzepte

### Data Model (DM)

DM ist zuständig für:

- Definition von Modellen und Feldern.
- Validierung von Werten und Typen.
- Beschreibung von Beziehungen zwischen Modellen.

Sie definieren Python-Klassen, die von DM-Basisklassen (z. B. `ModelWithUUID`) erben und `properties` und `types` verwenden.

### Storage

Die Storage-Schicht bietet:

- Abstraktion über SQL-Engines (MySQL, PostgreSQL usw.).
- Sessions und Transaktionen.
- Hilfsfunktionen für Abfragen und Filter.

Sie können zuerst ohne persistente Speicherung (nur in-memory) starten und später SQL-Storage hinzufügen.

### API

Die API-Schicht umfasst:

- Controller mit Geschäftslogik.
- Ressourcen, die DM-Modelle über HTTP zugänglich machen.
- Routen, die URLs und HTTP-Methoden auf Controller abbilden.
- Middlewares und WSGI-Anwendungen.

Sie können mit einem kleinen in-memory-Service beginnen und schrittweise DM und Storage für den Produktiveinsatz integrieren.

### OpenAPI (optional)

Mit OpenAPI-Integration können Sie:

- OpenAPI-Spezifikationen aus Controllern und Routen generieren.
- Spezifikationen über Ihr API ausliefern.
- Werkzeuge wie Swagger UI oder Client-Generatoren nutzen.

---

## Wann sollte man RESTAlchemy verwenden?

RESTAlchemy ist sinnvoll, wenn:

- **Sie** eine klare Trennung zwischen
  - Domänenmodellen (DM),
  - Storage-Details
  - und HTTP-API  
  benötigen, aber kein schwergewichtiges Framework einsetzen wollen.
- **Sie** ein typisiertes, validiertes Datenmodell wünschen.
- **Sie** Modelle schnell als REST-Ressourcen veröffentlichen möchten.
- **Ihnen** Migrationen und Schema-Evolution wichtig sind.

---

## Schnelle Navigation

Empfohlene Reihenfolge für neue Nutzer:

1. [Installation](installation.md)
2. [Getting started](getting-started.md) — kleiner in-memory-REST-Service.
3. Konzepte:
   - [Data model](concepts/data-model.md)
   - [API layer](concepts/api-layer.md)
   - [Storage layer](concepts/storage-layer.md)
4. How-to-Guides:
   - Basis-CRUD
   - Filtering, Sorting, Pagination
   - Beziehungen zwischen Modellen
5. Referenz:
   - `restalchemy.api.*`
   - `restalchemy.dm.*`
   - `restalchemy.storage.*`

Nach dem Lesen von nur:

- `installation.md`
- `getting-started.md`

sollten Sie in der Lage sein, einen funktionierenden Service zu erstellen.

---

## Beispiele

Praktische Beispiele finden Sie im Verzeichnis `examples/` des Repositories, insbesondere:

- `examples/restapi_foo_bar_service.py`  
  Einfacher REST-Service mit in-memory-Storage.
- `examples/dm_mysql_storage.py`  
  Datenmodell-Beispiel mit MySQL-Storage.
- `examples/openapi_app.py`  
  API-Beispiel mit OpenAPI-Spezifikation.
