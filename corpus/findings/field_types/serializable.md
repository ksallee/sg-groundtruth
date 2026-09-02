---
tags: [field-type, serializable, write, filter, operator, schema, error-handling, trap]
scope: api
summary: A structured blob stored on the row, which no filter can reach.
verdict: No operator works on a serializable field: every filter 400s as unfilterable. Task.splits answers a well-formed array of hashes with 200 while storing null, so REST cannot write it.
---

# serializable

**Data type** `serializable`, probed on `Task.splits` (stock, editable) and `Project.tracking_settings`
(stock, editable, read only here: a site-wide configuration object). The schema declares no structure:
`properties` holds `default_value` (null) and `summary_default`. On the probed site, a scan of all 114
entity types found six serializable fields and no others.

| field | editable | on a project-scoped entity |
|---|---|---|
| `Task.splits` | yes | yes |
| `Task.split_durations` | no | yes |
| `Project.tracking_settings` | yes | it is the project |
| `EventLogEntry.meta` | no | no |
| `SavedFilter.filters` | yes | no |
| `RvLicense.meta` | yes | no |

**Read** A decoded JSON object or array under `attributes`, never a string holding JSON, never under
`relationships`. One decode, not two.

```
GET /entity/projects/<id>?fields=tracking_settings -> 200
{"data":{"type":"Project","attributes":{"tracking_settings":{"navchains":{"Asset":"Asset.sg_asset_type",
 "Shot":"Shot.sg_sequence","Cut":"Cut.entity","CutItem":"CutItem.cut.entity"}}},
 "relationships":{},"id":<id>,"links":{"self":"/api/v1/entity/projects/<id>"}}}

EventLogEntry.meta, a deeper stored value; python types str, int, bool, NoneType, list:
{"type": "attribute_change", "attribute_name": "sg_versions", "entity_type": "Task",
 "entity_id": <id>, "in_create": true, "field_data_type": "multi_entity", "platform_id": null,
 "added": [{"name": "charA.jpg", "type": "Version", "id": <id>, "status": "rev", "uuid": "<uuid>"}],
 "removed": []}
```

**Write** `PUT /entity/tasks/<id>`, `Content-Type: application/json`. **`Task.splits` answers a well-formed
write with 200 and stores `null`.**

| sent | status | stored |
|---|---|---|
| `[]`, `[{}]`, `[{"foo": "bar"}]` | 200 | `null` |
| `[{"start_date": "2026-01-01", "end_date": "2026-01-02", "duration": 480}]` | 200 | `null` |
| `[{"note": "café 日本語 ✓"}]`, `[{"clé": 1}]` | 200 | `null` |
| two or more hashes in the array | 400 code 104, `undefined method '<' for nil` | n/a |
| `{"a": {"b": [1,2,3]}}` | 400 code 104, `no implicit conversion of String into Integer` | n/a |
| `[1,2,3]`, `[1,"two",null,true]`, 12 levels of `[[…]]` | 400 code 104, same message | n/a |
| `42`, `2.5`, `true`, `"hello"`, `'[{"a": 1}]'` | 400 code 103, wrong class | n/a |

```
code 103, source {} — the type layer, before the field sees the value:
 "API update() Task.splits expected [Hash,\n ActiveSupport::HashWithIndifferentAccess,\n
  ActionDispatch::Http::Parameters,\n ActionDispatch::Http::ParamsHashWithIndifferentAccess,\n
  Array,\n NilClass] data type(s) but got Integer: 42"

code 104, source null — the field's setter, on a value of an accepted class:
 "Update failed for [Task.splits]: no implicit conversion of String into Integer"
 "Update failed for [Task.splits]: undefined method '<' for nil"
```

Key order, numeric type and empty-container fidelity stay unproven on this site: a structure of an int, a
float, `true`, `false`, `null`, a nested list, `{}`, `[]`, a unicode value and an empty string was answered
200 and stored nothing.

**Size** One hash holding one long string, as `[{"note": "x" * n}]`. No request ceiling found; none of it
is stored, so this measures the request path and not the column.

| body | result |
|---|---|
| 1026 bytes | 200 in 0.4s |
| 100026 bytes | 200 in 0.4s |
| 1000026 bytes | 200 in 0.7s |
| 5000026 bytes | 200 in 1.0s |
| 7312 bytes, 100 well-formed split hashes | 400 code 104, `undefined method '<' for nil` |

**Clear**

| sent | result |
|---|---|
| `null` | 200, reads back `null` |
| `{}` | 200, reads back `null` |
| `[]` | 200, reads back `null` |
| `""` | 400 code 103, `... Array,\n NilClass] data type(s) but got String: ""` |
| never written | `null` |

There is no cleared-versus-empty distinction to read back, and on `Task.splits` no written state either.

**Filter** The type cannot appear in a filter. A bogus relation lists no `Valid relations`; there is no list.

```
[["splits", "definitely_not_an_operator", null]] -> 400
 {"status": 400, "code": 103,
  "title": "API read() Task.splits's 'serializable' data type cannot be used in a filter.",
  "source": {"Task.splits": " data type cannot be used in a filter. Value: {\"path\" => \"splits\",
             \"relation\" => \"definitely_not_an_operator\", \"values\" => [nil]}"}}
```

| filter | result |
|---|---|
| `is null`, `is_not null`, `is {}`, `contains "x"`, `in [[]]` | 400, the same title |
| the same on `Project.tracking_settings` | 400, the same title |

**Traps**
- **A client cannot query into a blob.** No operator means no `is None` to rank fill rate by (`probe 007`)
  and no way to find the rows holding a marker; `_summarize` (`probe 020`) has nothing to group on. Fetch
  rows on some other filter and inspect the decoded value client-side.
- **`Task.splits` answers 200 and stores nothing.** A client that writes state there and re-reads it cannot
  tell a discarded write from an empty field. Read back every serializable write.
- **Two failure layers, two error shapes.** A wrong Ruby class gives code 103 with the accepted-class list
  and an empty `source`; a right class the setter chokes on gives code 104 with a raw Ruby message and
  `source: null`. Neither names the key at fault.
- **The column takes arbitrary JSON; the field refuses it.** `EventLogEntry.meta` holds nested objects,
  lists, booleans and nulls, so the storage is a blob. Of the four editable fields three are outside a
  project: `Project.tracking_settings` is site configuration, `SavedFilter.filters` and `RvLicense.meta`
  have no `project` field. A project-scoped blob to write does not exist here.
