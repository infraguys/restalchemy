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

# Besonderheiten der Serialisierung von Action-Ergebnissen

Dieses Dokument beschreibt eine wichtige Nuance in RESTAlchemy: **wie Serializer (Packer) und das Feld-Set eines Resources bei der Verarbeitung von `actions` ausgewählt werden**, und warum eine Action, die auf einem Controller für Resource `A` definiert ist, standardmäßig *als Resource `A`* serialisiert wird – selbst wenn sie tatsächlich ein Modell `B` zurückgibt.

Außerdem wird ein praktikabler Workaround (ohne Änderungen an der Bibliothek) beschrieben und auf ein funktionierendes Beispiel in den Functional Tests verwiesen.

---

## TL;DR

- Eine Action wird **im Kontext des Controllers** ausgeführt, auf dem sie definiert bzw. an den sie gebunden ist.
- **Packer und Serialisierungsschema werden aus `__resource__` dieses Controllers genommen.**
- Gibt eine Action ein Modell eines anderen Typs zurück, versucht der Packer „fremde“ Felder zu lesen und scheitert mit `AttributeError`.
- Praktischer Workaround ohne RESTAlchemy zu verändern: **Action an einen dedizierten Controller binden**, dessen `__resource__` dem Rückgabe-Typ entspricht.

---

## 1. Warum passiert das?

### 1.1. Grober Ablauf der Action-Verarbeitung

Vereinfacht für eine URL wie:

- `/v1/vms/<uuid>/actions/ip_addresses`

passiert:

1. Der Router löst den Route-Baum auf (z. B. `v1 → vms → actions/ip_addresses`).
2. VM wird über `<uuid>` geladen (das ist der **Input** der Action).
3. Die Action-Klasse (`routes.Action`) wird aufgelöst und ihr `__controller__` bestimmt.
4. Die Controller-Methode mit `@actions.get` / `@actions.post` wird aufgerufen.
5. Das Ergebnis wird an `controller.process_result()` übergeben.
6. `process_result()` baut die HTTP-Response über `controller.get_packer()`.
7. Der Packer serialisiert anhand der **Resource-Felder aus `controller.__resource__`**.

### 1.2. Die zentrale Nuance

Der Packer „errät“ den Modelltyp zur Laufzeit nicht aus dem Rückgabewert (OpenAPI-Annotationen werden zur Laufzeit nicht zum Packen verwendet). Stattdessen wird die Response **als die Resource serialisiert, die an den Controller gebunden ist**.

Wenn der Controller deklariert:

- `__resource__ = ResourceByRAModel(models.VM)`

dann erwartet der Packer VM-Felder (z. B. `state`, `name`, ...).

---

## 2. Symptome

### 2.1. Typischer Error-Stack

Gibt eine Action auf dem VM-Controller ein `IpAddress` zurück, versucht der Packer (serialisiert „als VM“) das Feld `state` bei `IpAddress` zu lesen:

- `AttributeError: IpAddress object has no attribute state`

Das wirkt wie „kaputte Serialisierung in Actions“, ist aber eigentlich **ein Mismatch zwischen `__resource__` des Controllers und dem tatsächlichen Ergebnis-Typ**.

---

## 3. Praxisbeispiel aus den Functional Tests (VM → IpAddress)

### 3.1. Ziel

Ein Action-Endpunkt:

- `GET /v1/vms/<uuid>/actions/ip_addresses`

soll **eine Liste von `IpAddress`** für die VM zurückgeben.

### 3.2. Warum es nicht reicht, `IpAddress` direkt aus `VMController` zurückzugeben

Wenn `ip_addresses()` direkt in `VMController` implementiert wird, wird weiterhin „als VM“ serialisiert und es kommt zum Fehler (siehe Abschnitt 2).

### 3.3. Fix ohne Änderungen an der Bibliothek (Ansatz 1)

Der Fix besteht aus zwei Teilen:

- **(A) Dedizierter Controller für das Action-Ergebnis** mit korrektem `__resource__`.
- **(B) Action-Route an diesen Controller binden**.

#### A) Ergebnis-Controller

Datei:

- `restalchemy/tests/functional/restapi/ra_based/microservice/controllers.py`

Klasse:

- `VMIpAddressesController`

Idee: Der Input-Parameter `resource` ist weiterhin VM (Parent Resource), aber **`__resource__` ist IpAddress**, sodass der Packer korrekt serialisiert.

Zusätzliche Nuance: RESTAlchemy hält eine globale Zuordnung `model → resource`.

- Wenn ein weiteres `ResourceByRAModel(models.IpAddress)` erstellt wird, kommt es zu einem Duplicate-Mapping-Fehler.
- Deshalb wird die Resource **wiederverwendet**: `IpAddressController.__resource__`.

#### B) Action-Route

Datei:

- `restalchemy/tests/functional/restapi/ra_based/microservice/routes.py`

Klasse:

- `VMIPAddressesAction`

Sie muss auf `VMIpAddressesController` zeigen, und in `VMRoute` wird sie so deklariert:

- `ip_addresses = routes.action(VMIPAddressesAction, invoke=False)`

### 3.4. Test für das korrekte Verhalten

Datei:

- `restalchemy/tests/functional/restapi/ra_based/test_resources.py`

Test:

- `TestRetryOnErrorMiddlewareBaseResourceTestCase.test_vm_get_ip_addresses_action_returns_success`

Er prüft:

- HTTP 200
- JSON-Response ist eine Liste von IpAddress-Objekten mit:
  - `uuid`
  - `ip`
  - `port` (URI des Ports)

---

## 4. Empfehlungen

### 4.1. Dedizierten Controller verwenden (empfohlen)

Nutze einen dedizierten Controller, wenn:

- die Action **einen anderen Modelltyp** (oder eine Liste davon) zurückgibt,
- du einen Action-Endpunkt beibehalten willst,
- du RESTAlchemy nicht ändern möchtest.

Das liefert:

- den passenden Packer,
- das passende Feld-Set,
- vorhersagbares Verhalten.

### 4.2. `dict` / Primitive zurückgeben

Wenn das Ergebnis keine Resource/kein Modell ist (z. B. `{"state": "on"}`), sind einfache Strukturen (`dict`, `list[dict]`, Strings) sinnvoll, da sie nicht von `__resource__` abhängen.

### 4.3. Eine Action, mehrere Rückgabe-Typen

Wenn eine Action mehrere Typen zurückgeben kann (manchmal VM, manchmal IpAddress), ist das ein ungünstiger Vertrag:

- eine einzelne `__resource__` kann nicht beide Typen korrekt serialisieren.

Dann lieber:

- separate Endpunkte/Controller,
- oder die Bibliothek erweitern (z. B. „action-specific resource type“).

---

## 5. Siehe auch

- How-to zu Nested Resources und Actions:
  - `docs/de/how-to/api-nested-resources-and-actions.md`
