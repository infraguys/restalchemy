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

Ein Array-Feld — der übliche Fall ist `ModelWithTags` mit seinem `tags` —
verhält sich anders, und über diesen Unterschied stolpert man leicht:

```http
GET /v1/tagged/?tags=env:prod
```

bedeutet `tags = ARRAY['env:prod']`: Das gesamte Array ist gleich diesem
einen Element. Das ist ein gültiger Filter, aber keine Suche — eine Zeile
mit den Tags `['env:prod', 'region:eu']` passt nicht.

Die Suche nach Elementen erfolgt über einen Operator, der als Suffix am
Parameternamen steht:

- `field__contains_all=a` — `field @> ARRAY['a']`, das Array enthält alle
  aufgeführten Elemente.
- `field__contains_any=a` — `field && ARRAY['a']`, das Array enthält
  mindestens eines der aufgeführten Elemente.

Wiederholen Sie den Parameter, um weitere Elemente zu nennen. Anders als
bei einem skalaren Filter sind die Wiederholungen Elemente eines einzigen
Arrays und keine Alternativen:

```http
GET /v1/tagged/?tags__contains_all=env:prod&tags__contains_all=region:eu
```

trifft Zeilen mit **beiden** Tags, während

```http
GET /v1/tagged/?tags__contains_any=env:prod&tags__contains_any=env:staging
```

Zeilen mit **einem der beiden** trifft.

Der Operator steht im Parameternamen und nicht im Wert, weil die Werte
selbst Satzzeichen tragen — `owner:user:<uuid>` ist eine verbreitete Form —
und eine Form `op:value` deshalb mehrdeutig wäre.

Beachten Sie: `ContainsAll`/`ContainsAny` werden zu Array-Operatoren von
PostgreSQL übersetzt. Unter MySQL wird die Anfrage abgelehnt, sobald der
Filter die Storage-Schicht erreicht.

### Was abgelehnt wird

Beides beantwortet ein `400`:

- ein Operator auf einem Feld, das kein Array ist
  (`?name__contains_all=x`) — das erzeugte SQL würde erst weiter unten und
  mit einer schlechteren Meldung scheitern;
- zwei Arten, ein Feld zu filtern (`?tags=a&tags__contains_all=b` oder
  `contains_all` zusammen mit `contains_any`) — Filter werden nach
  Feldnamen abgelegt, der zweite würde den ersten also ersetzen, statt die
  Auswahl einzuschränken.

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
GET /v1/tagged/?tags__contains_all=env:prod&page_limit=50
```

Der selektive Fall bleibt auf dem GIN-Index, der Cursor wirkt als
gewöhnlicher Filter auf den Zeilen, die der Index liefert.

---

## Benutzerdefinierte Eigenschaften

Filter auf benutzerdefinierten (nicht gespeicherten) Eigenschaften werden
erst nach der Abfrage in Python angewandt, und dort sind nur `EQ` und `In`
unterstützt — alles andere, Array-Operatoren eingeschlossen, ergibt ein
`400`.

---

## Siehe auch

- [Filter-Referenz](../reference/dm/filters.md) — die Klausel-Klassen
  selbst, einschließlich `JSONFields` für `jsonb`-Spalten.
- [Modell-Referenz](../reference/dm/models.md) — `ModelWithTags`.
- [Basis-CRUD](api-basic-crud.md) — woher `process_filters` kommt.
