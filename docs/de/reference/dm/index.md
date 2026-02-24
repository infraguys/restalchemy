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

# Data Model (DM) Referenz

Dieser Abschnitt beschreibt die Data Model (DM) Schicht in RESTAlchemy.

Die DM-Schicht ist verantwortlich für:

- Definition von Domänenmodellen als Python-Klassen.
- Beschreibung von Feldern, Typen und Validierungsregeln.
- Abbildung von Beziehungen zwischen Modellen.
- Bereitstellung von Mixins für häufige Muster (UUID, Timestamps, Name/Beschreibung usw.).

Die DM-Schicht ist in folgenden Modulen implementiert:

- `restalchemy.dm.models`
- `restalchemy.dm.properties`
- `restalchemy.dm.relationships`
- `restalchemy.dm.types`
- `restalchemy.dm.filters`
- `restalchemy.dm.types_dynamic` (erweiterte Typen)
- `restalchemy.dm.types_network` (netzwerkbezogene Typen)

Diese Referenz konzentriert sich auf die ersten fünf Module, die im Alltag am häufigsten verwendet werden.

---

## Kurzer Überblick

Ein typisches DM-Modell sieht so aus:

```python
from restalchemy.dm import models, properties, types


class Foo(models.ModelWithUUID):
    # Integer field, required
    value = properties.property(types.Integer(), required=True)

    # Optional string with default value
    description = properties.property(types.String(max_length=255), default="")
```

Wichtige Ideen:

- Sie erben von `Model` oder einer Hilfsklasse wie `ModelWithUUID`.
- Sie verwenden `properties.property()`, um Felder zu definieren.
- Sie verwenden `types.*` Klassen, um Typ und Constraints eines Feldes zu beschreiben.

Beziehungen zwischen Modellen werden mit `relationships.relationship()` definiert.

Filter (`restalchemy.dm.filters`) beschreiben Abfragebedingungen in Storage- und API-Schichten.

---

## Dateien in diesem Abschnitt

- [Modelle](models.md)
  - `Model`, `ModelWithID`, `ModelWithUUID`, `ModelWithTimestamp` und weitere Mixins.
- [Properties](properties.md)
  - Property-System: `Property`, `IDProperty`, `PropertyCollection`, `PropertyManager`, Fabriken.
- [Relationships](relationships.md)
  - `relationship()`, `required_relationship()`, `readonly_relationship()`, `Relationship`, `PrefetchRelationship`.
- [Types](types.md)
  - Skalare, Datums-/Zeit-, Collection- und strukturierte Typen für Properties.
- [Filters](filters.md)
  - Filter-Klassen (`EQ`, `GT`, `In` usw.) und logische Ausdrücke (`AND`, `OR`).

Sie finden die DM-Referenz in jeder Sprache im entsprechenden Abschnitt `reference/dm/`.
