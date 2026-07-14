<!--
Copyright 2026 Genesis Corporation

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

# Batch requests

Diese Anleitung zeigt, wie Clients mehrere logische Operationen
(create/get/update/delete sowie Controller-Actions) in einem einzigen
HTTP-Aufruf bündeln können, mit Hilfe von `restalchemy.api.batch`.

Jedes Element eines Batches wird als eigenständige Anfrage durch den
*unveränderten* Routing-/Controller-/Packer-Stack abgespielt — an
bestehenden `Controller`- oder `Route`-Subklassen muss dafür nichts
geändert werden.

---

## 1. Endpunkt aktivieren

Hängen Sie `batch.BatchRoute` an Ihre Root-Route, genauso wie jede andere
Route:

```python
from restalchemy.api import batch
from restalchemy.api import routes


class Root(routes.RootRoute):
    v1 = routes.route(V1Route)
    batch = routes.route(batch.BatchRoute)
```

Damit steht ein einziger `POST /batch/`-Endpunkt bereit, der jede von
`Root` aus erreichbare Ressource ansprechen kann — eine Aktivierung pro
Ressource ist nicht nötig.

---

## 2. Request-Format

```json
{
  "requests": [
    {"method": "POST", "path": "/v1/vms/", "body": {"name": "vm-a"}},
    {"method": "GET",  "path": "/v1/vms/<uuid>"},
    {"method": "PUT",  "path": "/v1/vms/<uuid>", "body": {"name": "vm-b"}},
    {"method": "DELETE", "path": "/v1/vms/<uuid>"},
    {"method": "POST", "path": "/v1/vms/<uuid>/actions/poweron/invoke"}
  ]
}
```

Jedes Element in `requests`:

| Feld      | erforderlich | Beschreibung                                                |
|-----------|---------------|--------------------------------------------------------------|
| `method`  | ja            | `GET`, `POST`, `PUT` oder `DELETE` — wie bei einer echten Anfrage. |
| `path`    | ja            | Der Pfad, den Sie normalerweise aufrufen würden, inklusive Query-String (`?field=value`) für Filterung. |
| `body`    | nein          | JSON-Body im gleichen Format wie beim echten Endpunkt.        |
| `headers` | nein          | Zusätzliche Header, die nur für dieses Element gelten.         |

---

## 3. Jedes Element läuft unabhängig, durch den vollständigen Middleware-Stack

Jedes Element ist Best-effort: der Fehler eines Elements stoppt oder
verwirft nicht die anderen. Die Antwort ist immer `200 OK` mit einem
`status`/`body`-Paar pro Element, selbst wenn einzelne Elemente
fehlgeschlagen sind — prüfen Sie den `status` jedes Elements einzeln,
verlassen Sie sich nicht auf den äußeren HTTP-Status.

Jedes Element wird durch den *gesamten* WSGI-Middleware-Stack geleitet, der
den `/batch`-Endpunkt umschließt (Auth, routenspezifische
Autorisierung/Policy, Rate-Limiting, Retry-on-Deadlock, ...) — nicht nur
durch die innere Routing-/Controller-Schicht. Ein Batch-Element unterliegt
damit genau denselben Regeln wie ein direkter Aufruf desselben Pfads: wenn
eine Middleware einen direkten `POST /v1/vms/` ablehnen oder drosseln
würde, lehnt sie denselben Request auch ab, wenn er als Batch-Element
ankommt.

Eine Konsequenz daraus, dass jedes Element den vollständigen Stack
durchläuft: Wenn die `ContextMiddleware` der Anwendung pro Request eine
DB-Transaktion öffnet, erhält jedes Element seine *eigene* Transaktion — es
gibt keine elementübergreifende Atomarität. Ein Batch mit fünf
Schreiboperationen sind fünf unabhängige Transaktionen, genau als hätten
Sie fünf separate direkte Aufrufe gemacht; ein Fehler in Element 3 hat
keine Auswirkung auf Element 1, 2, 4 oder 5. Wenn mehrere Schreibvorgänge
gemeinsam gelingen oder scheitern müssen, muss das als eigene Operation auf
der Zielressource implementiert werden (ein einzelner Endpunkt, der alle
Änderungen in einer Transaktion durchführt), nicht durch Batching
unabhängiger Aufrufe.

---

## 4. Response-Format

```json
[
  {"status": 201, "body": {"uuid": "...", "name": "vm-a", "...": "..."}},
  {"status": 200, "body": {"uuid": "...", "name": "vm-a", "...": "..."}},
  {"status": 200, "body": {"uuid": "...", "name": "vm-b", "...": "..."}},
  {"status": 204, "body": null},
  {"status": 200, "body": {"uuid": "...", "state": "on", "...": "..."}}
]
```

Die Antwort ist ein JSON-Array, ein Eintrag pro Request, **in derselben
Reihenfolge wie gesendet**. Jeder Eintrag entspricht dem, was ein direkter
Aufruf des jeweiligen Endpunkts geliefert hätte: der reale HTTP-Statuscode
und der geparste Response-Body (oder `null` bei leerem Body). Ein
fehlgeschlagenes Element sieht aus wie jeder andere RestAlchemy-Fehler-Body:

```json
{"status": 404, "body": {"type": "RecordNotFound", "code": 404, "message": "..."}}
```

---

## 5. Limits und Validierungsfehler

- `requests` muss ein JSON-Array sein; alles andere wirft für den gesamten
  Aufruf `ParseError` (HTTP 400).
- `BatchController.__max_batch_size__` (Standard `100`) begrenzt die
  Anzahl der Elemente pro Aufruf; wird das überschritten, wirft der
  gesamte Aufruf `BatchSizeLimitExceeded` (HTTP 400), noch bevor
  irgendein Element ausgeführt wird. Überschreiben Sie das Attribut in
  einer Subklasse, falls Sie ein anderes Limit brauchen.
- Ein Batch-Element darf nicht den Batch-Endpunkt selbst ansprechen
  (`NestedBatchNotAllowed`, HTTP 400) — das wird abgelehnt statt zu
  rekursieren.

---

## Zusammenfassung

- `batch.BatchRoute`/`batch.BatchController` verwenden den bestehenden
  Routenbaum, die Controller und Packer unverändert weiter — Batching ist
  rein additiv.
- Jedes Element ist Best-effort und unabhängig: prüfen Sie den `status`
  jedes Elements.
- Elemente durchlaufen den vollständigen Middleware-Stack, sodass
  Auth/Policy/Rate-Limiting/Retry sich genau wie bei einem direkten Aufruf
  verhalten — auf Kosten einer elementübergreifenden Transaktion: jedes
  Element bekommt seine eigene.
- Actions (`.../actions/<name>/invoke`) funktionieren innerhalb eines
  Batches genau wie bei einem direkten Aufruf, da ein Batch-Element nur
  eine Wiedergabe von Pfad/Methode/Body ist.
