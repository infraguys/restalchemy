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

# Sammlungen über HTTP filtern

Dieses How-to beschreibt die Query-Parameter, die ein Sammlungs-Endpunkt
(die Methode `FILTER`) versteht, und wie daraus
[DM-Filter](../reference/dm/filters.md) werden.

Die Filterung wird pro Ressource aktiviert:

```python
class TaggedController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        TaggedModel,
        process_filters=True,
    )
```

Ohne `process_filters=True` werden die Parameter unverändert als
Zeichenketten durchgereicht und weder geparst noch validiert.

---

## Skalare Felder

Ein Parameter, der nach einem Feld benannt ist, filtert auf Gleichheit; der
Wert wird in den Feldtyp geparst, sodass ein vom Typ abgelehnter Wert ein
`400` ergibt und nicht einen Vergleich, der still auf nichts passt:

```http
GET /v1/vms/?name=web-1          ->  EQ("web-1")
GET /v1/vms/?name=web-1&name=web-2  ->  In(["web-1", "web-2"])
```

Ein wiederholter Parameter liest sich damit als „eines davon“.

---

## Array-Felder

Ein Array-Feld (`ModelWithTags` und sein `tags` sind der übliche Fall)
verhält sich anders, und über diesen Unterschied stolpert man leicht:

```http
GET /v1/tagged/?tags=env:prod
```

bedeutet `tags = ARRAY['env:prod']` — das ganze Array ist gleich diesem
einen Element. Das ist ein gültiger Filter, aber keine Suche: Eine Zeile
mit den Tags `['env:prod', 'region:eu']` passt nicht.

Die Suche nach einem Element ist genau das, wofür der Filterausdruck
weiter unten da ist — `?q=tags:"env:prod"` —, und es gibt keinen
Feldparameter, der das täte. Der Grund liegt in den Werten: Ein Tag sieht
aus wie `owner:user:<uuid>`, samt Interpunktion, und ein Parameter, dessen
Wert eigene Trennzeichen trägt, kann nicht zusätzlich einen Operator
tragen. Ein Ausdruck kann es, denn er hat Anführungszeichen.

---

## Filterausdrücke

Die Parameter oben sind ein AND aus Gleichheiten und sonst nichts. Wo das
nicht reicht — OR, Klammerung, Negation, Bereiche —, nimmt ein
Sammlungs-Endpunkt zusätzlich einen Ausdruck entgegen, in einer Teilmenge
von [AIP-160](https://google.aip.dev/160), in einem einzigen Parameter:

```http
GET /v1/vms/?q=name = "web-1" AND size > 10
GET /v1/vms/?q=tags:"env:prod" OR tags:"env:staging"
GET /v1/vms/?q=NOT (state = error) AND created_at >= "2026-07-01T00:00:00Z"
```

Der Parameter heißt standardmäßig `q`. Wo die Sprache eingeschaltet ist,
wird der Name aus dem Namensraum der Felder herausgenommen; eine Ressource
mit einem Feld namens `q` benennt ihn also um — oder schaltet die Sprache
ab, und der Parameter bedeutet wieder, was er vorher bedeutet hat:

```python
class VmController(controllers.BaseResourceController):
    __filter_param__ = "filter"   # oder None, um die Sprache abzuschalten
```

### Operatoren

| Geschrieben | Wird zu | |
|---|---|---|
| `name = "web-1"` | `EQ` | |
| `name != "web-1"` | `NE` | |
| `size > 10`, `>=`, `<`, `<=` | `GT`, `GE`, `LT`, `LE` | |
| `name = null` | `Is(None)` | `!= null` ergibt `IsNot(None)` |
| `tags:"env:prod"` | `ContainsAll` | ein Array enthält das Element |
| `description:*` | `IsNot(None)` | das Feld ist gesetzt |
| `spec.kind = "totp"` | `JSONFields` | ein Schlüssel in einer `jsonb`-Spalte |
| `AND` `OR` `NOT` `(...)` | `AND` `OR` `NOT` | Schlüsselwörter in Großbuchstaben |

Zwei Dinge überraschen regelmäßig, beide von AIP-160 geerbt.

`OR` bindet **stärker** als `AND`: `a = 1 OR b = 2 AND c = 3` liest sich
als `(a = 1 OR b = 2) AND c = 3`. Im Zweifel klammern.

Leerraum zwischen zwei Restriktionen ist ein implizites `AND`, `name =
web-1 size > 10` ist also eine Konjunktion.

### Anführungszeichen

Ein Wert, der `:`, `.` oder ein Leerzeichen trägt, muss in
Anführungszeichen stehen, sonst liest sich seine Interpunktion als weitere
Syntax:

```http
?q=tags:"env:prod"                       # richtig
?q=tags:env:prod                         # 400 — das zweite : ist ein Operator
?q=created_at >= "2026-07-01T00:00:00Z"
```

Ohne Anführungszeichen sind `null`, `true`, `false` und `*` Literale der
Sprache; in Anführungszeichen sind es genau diese Zeichenketten.

### Beide oder eines

Für `ContainsAny` gibt es keinen eigenen Operator, und es braucht auch
keinen. `tags:"a"` ist `tags @> ARRAY['a']`, die booleschen Operatoren
sagen es also bereits:

```http
?q=tags:"env:prod" AND tags:"region:eu"    ->  tags @> ARRAY[...]   beide
?q=tags:"env:prod" OR tags:"env:staging"   ->  tags && ARRAY[...]   eines
```

Klauseln auf einem Feld werden zu einem einzigen Array-Operator
zusammengefasst, jede der beiden Formen ist damit ein Indexzugriff statt
einem pro Element. `name = a OR name = b` wird genauso zusammengefasst, zu
`name = ANY(...)`.

Das Zusammenfassen ändert nie, wonach ein Ausdruck fragt. `@>` über
mehrere Elemente ist nicht deren Vereinigung, deshalb behält eine bereits
per `AND` verbreiterte Containment-Prüfung ihren eigenen Operator, wenn
sie danach per `OR` verknüpft wird:

```http
?q=(tags:"a" AND tags:"b") OR tags:"c"   ->  tags @> ARRAY['a','b'] OR tags @> ARRAY['c']
```

Dieses Zusammenfassen ist der Grund, warum die Query-Parameter-Form zwei
Operatornamen braucht und der Ausdruck keinen: eine Parameterliste hat
weder AND noch OR, um den Unterschied zu tragen.

### Zusammen mit den Feldparametern

Beide werden per AND verbunden und lassen sich frei mischen:

```http
GET /v1/vms/?state=active&q=tags:"env:prod" OR tags:"env:staging"
```

### Wofür ein Ausdruck abgelehnt wird

Jeder dieser Fälle ist ein `400` und nie ein Filter, der still etwas
anderes tut:

- ein Feld, das die Ressource nicht hat, oder ein Wert, den ihr Typ
  ablehnt;
- ein Feld, das die Ressource aus Antworten ausblendet — über
  `hidden_fields` oder `Permissions.HIDDEN` für die Methode `FILTER`.
  Ein Vergleich gegen ein Feld, das die API nie zurückgibt, gäbe es Bit
  für Bit preis; ein verborgenes Feld antwortet daher genau wie ein
  unbekanntes. Dieselbe Regel gilt für einen Feldparameter (`?secret=x`)
  und für `sort_key`, der die Sammlung nach einem Wert ordnet, den er
  nie zeigt;
- ein Ausdruck, der eine benutzerdefinierte Eigenschaft nennt (siehe
  unten);
- ein Operator, den der Storage-Dialekt nicht übersetzen kann — `:` und
  `spec.kind` gibt es nur unter PostgreSQL;
- mehr als ein `q` in einer Anfrage: ob die beiden per AND oder per OR zu
  verbinden wären, steht nicht in der Anfrage;
- ein Ausdruck mit über 100 Knoten, tiefer als 8 verschachtelt oder länger
  als 4096 Zeichen — die Grenzen sind `__filter_max_nodes__`,
  `__filter_max_depth__` und `__filter_max_length__` am Controller, und es
  gibt sie, weil ein Filterstring nicht vertrauenswürdige Eingabe ist. Die
  Länge wird zuerst geprüft: die beiden anderen zählt erst das Parsen, und
  das Parsen beginnt damit, die ganze Zeichenkette zu scannen.

Bewusst ausgelassen: Funktionen (`f(x)`), ein bloßes Literal als unscharfe
Suche über alle Felder, `-` als Synonym für `NOT`, Wildcards in `=`,
Vergleich von Feld mit Feld und Traversierung tiefer als ein Schlüssel.

---

## Indizes

Ein Array-Filter ist nur so gut wie sein Index. Deklarieren Sie den
GIN-Index in derselben Migration, die die Tabelle anlegt:

```sql
CREATE INDEX idx_tagged_tags ON tagged USING GIN (tags);
```

Bei einem selektiven Wert — einem Tag, den nur ein kleiner Teil der Zeilen
trägt, so wie ein Besitzer- oder Identitäts-Tag — antwortet der Planer aus
dem Index. Bei einem Wert, den fast jede Zeile trägt, läuft er stattdessen
über den Primärschlüssel und wendet den Tag als Filter an; unter einem
`LIMIT` ist das der günstigere Plan und kein fehlender Index.

---

## Filtern zusammen mit Pagination

Pagination und Filter greifen ineinander: Die Grenze des Cursors wird per
AND an das gehängt, wonach der Aufrufer gefiltert hat, und beide reisen
gemeinsam weiter.

```http
GET /v1/tagged/?project_id=<uuid>&page_limit=50
```

Der selektive Fall bleibt auf dem GIN-Index, der Cursor wirkt als
gewöhnlicher Filter auf den Zeilen, die der Index liefert.

Ein Ausdruck paginiert genauso: Der Cursor wird aus den Feldparametern
gebaut, der Ausdruck kommt unmittelbar danach per AND hinzu:

```http
GET /v1/tagged/?q=tags:"env:prod"&page_limit=50&page_marker=<uuid>
```

Schicken Sie denselben Ausdruck bei jeder Seite mit. Ein Cursor bedeutet
nur etwas in Bezug auf den Filter, unter dem er ausgegeben wurde; wird der
Filter mitten im Durchlauf geändert, werden Zeilen übersprungen oder
doppelt geliefert. Bedenken Sie außerdem, dass Keyset-Pagination sich auf
den Index hinter `ORDER BY` stützt und ein `OR` über mehrere Felder den
Planer davon abbringen kann — grenzen Sie ein, wo es mit Feldparametern
geht.

---

## Benutzerdefinierte Eigenschaften

Filter auf benutzerdefinierten (nicht gespeicherten) Eigenschaften werden
erst nach der Abfrage in Python angewandt, und dort sind nur `EQ` und `In`
unterstützt — alles andere, Array-Operatoren eingeschlossen, ergibt ein
`400`.

Der Ausdrucksparameter erreicht sie überhaupt nicht. Sie werden über die
Zeilen gefiltert, die die Abfrage bereits geliefert hat, und ein Ausdruck
lässt sich nicht in eine Storage-Hälfte und eine Python-Hälfte zerlegen:
`stored = 1 OR custom = 2` ließe sich nirgends auswerten. Eine solche
Eigenschaft in `q` zu nennen ist ein `400`; `?custom=2` funktioniert
weiterhin.

---

## Siehe auch

- [Filter-Referenz](../reference/dm/filters.md) — die Klausel-Klassen
  selbst, einschließlich `JSONFields` für `jsonb`-Spalten.
- [Modell-Referenz](../reference/dm/models.md) — `ModelWithTags`.
- [Basis-CRUD](api-basic-crud.md) — woher `process_filters` kommt.
