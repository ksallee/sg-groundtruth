---
tags: [field-type, status, list-field, filter, operator, write, schema, trap]
scope: api
verdict: REST does not enforce hidden_values: a project-hidden status writes and reads back fine, so every client must subtract it itself. Only valid_values is enforced.
---

# status_list

**Data type** `status_list`. Probed on `Version.sg_status_list` (stock, editable). Properties are always
the same five keys: `default_value`, `display_values`, `hidden_values`, `summary_default`, `valid_values`.

| field | `default_value` | `valid_values` |
|---|---|---|
| `Version.sg_status_list` | `rev` | 16 |
| `Shot.sg_status_list` | `wtg` | 10 |
| `Shot.sg_latest_vendor_status` | `wtg` | 6 |

**Read** A bare code string under `attributes`, never an object and never a relationship. No entity stands
behind it, so a dotted path is dropped at 200 (probe 004); the label comes only from `display_values` (probe 009).

```
one row: {"type": "Version", "attributes": {"code": "sh010_comp_v001", "sg_status_list": "fin"}, "relationships": {}, "id": <id>}
  attributes keys ['code', 'sg_status_list']   relationships keys []
  distinct over 100 versions: {"rev": 29, "na": 28, "vwd": 21, "apr": 20, "fin": 2}
  'rev' has no label inline; display_values -> 'Pending Review'
  ?fields=sg_status_list.Status.name -> 200 {"sg_status_list": "fin"}    (the dotted key is absent)
```

**Write** A raw code, on POST and on PUT.

| sent | result |
|---|---|
| key omitted on create | 201, `default_value` applied -> `rev` |
| `"part"` on create (hidden in the project) | 201, stored as `part` |
| `"fin"` (usable code) | 200, reads back `fin` |
| `"part"` (hidden in the project) | 200, reads back `part` |
| `"Final"` (display label) | 400, prior value unchanged |
| `"zznope"` (not in `valid_values`) | 400, prior value unchanged |

```
400 {"status": 400, "code": 104, "source": null, "detail": null, "meta": null,
     "title": "Update failed for [Version.sg_status_list]: 'Final' is not a valid status. Valid statuses:
               'na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl',
               'pndvs', 'part', 'pass', 'pndng'."}
'zznope' -> same shape: "'zznope' is not a valid status. Valid statuses: <the same 16>"
```

The 400 enumerates site-wide `valid_values`, hidden codes included; the write path never consults `hidden_values`.

**Clear**

| sent | result |
|---|---|
| `null` | 200, reads back `None` |
| `""` | 200, reads back `None` |

`default_value` is applied only when the key is absent on create, never on a clear. Cleared rows stay
filterable: `[["sg_status_list", "is", null]]` returns 1 in the sandbox after the clears.

**Filter** Four operators only, no substring family at all:

```
  sg_status_list definitely_not_an_operator 'x' -> 400
  title:  "API read() Version.sg_status_list's 'status_list' data type doesn't support
           'definitely_not_an_operator' 'relation'"
  source: {"Version.sg_status_list": " data type doesn't support 'definitely_not_an_operator' 'relation'.
       Value: {"path" => "sg_status_list", "relation" => "definitely_not_an_operator", "values" => ["x"]}
       Valid relations: ["is", "is_not", "in", "not_in"]"}
```

Value format is the raw code, or a list of raw codes for `in`/`not_in`. Baseline 100 versions:

| filter | rows |
|---|---|
| `is "rev"` | 29 |
| `is_not "rev"` | 71 |
| `in ["rev", "fin"]` | 31 |
| `not_in ["rev", "fin"]` | 69 |
| `is "Pending Review"` (display label) | 0 |
| `in ["Pending Review", "Final"]` | 0 |
| `is "zznope"` (not in `valid_values`) | 0 |
| `in ["zznope"]` | 0 |
| `is null` | 0 |
| `is "part"` (hidden in the project) | 0 |
| `contains "re"` / `starts_with "r"` / `ends_with "v"` | 400 `doesn't support ... 'relation'` |

Write and filter disagree on the same value:

| value | write | filter |
|---|---|---|
| display label (`"Final"` written, `"Pending Review"` filtered) | 400 | 0 rows |
| `"zznope"` (not in `valid_values`) | 400 | 0 rows |
| `"part"` (hidden in the project) | 200, stored | 0 rows |

Byte-identical to a plain `list` field (`Version.sg_version_type`): the two types filter the same and
differ only in that `status_list` adds `hidden_values` and an Icon (probe 010). Both are a strict
subset of text's eight (probe 017): `contains`, `not_contains`, `starts_with`, `ends_with` are 400s here.

**Traps**
- `hidden_values` is not enforced by the API. REST 201s and 200s on a status the project's UI refuses to
  offer, so **every client must subtract `hidden_values` itself** (probe 009). The API will not do it.
  Conversely, do not treat a hidden code read back off an entity as corrupt: it is a legal stored value.
- **Permitted is not safe.** An operator reports that a hidden status set this way can break the web UI for
  that entity. Unverified: it is not observable through the API (see `docs/quirks.md`). Until someone
  checks it in a browser, treat writing a hidden status as something to avoid, not merely as something the
  server allows.
- A wrong code in a filter is a silent 0 rows, indistinguishable from a status nothing holds.
- Display labels are accepted nowhere. Round-trip through `display_values` in both directions, and fall
  back to the raw code when a key is missing.
- No substring operator, so there is no server-side type-ahead over statuses. Fetch `valid_values` once
  and filter the list client-side. Sorting and filtering is on the code, which is not alphabetical by label.
- Codes are per entity type: `Version` has 16, `Shot` 10, `Shot.sg_latest_vendor_status` 6. Never reuse a
  code across types, and read the schema per field, not per entity.

**Python equivalent**

```python
# usable statuses for a project, then set one
f = sg.schema_field_read("Version", "sg_status_list", project_entity={"type": "Project", "id": pid})
p = f["sg_status_list"]["properties"]
usable = [v for v in p["valid_values"]["value"] if v not in p["hidden_values"]["value"]]
sg.update("Version", vid, {"sg_status_list": "fin"})   # code, not "Final"
sg.update("Version", vid, {"sg_status_list": None})    # clear; "" works too
sg.find("Version", [["sg_status_list", "in", ["rev", "fin"]]])
```
