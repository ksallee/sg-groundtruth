---
tags: [field-type, jsonb, serializable, write, filter, operator, schema, error-handling, trap]
scope: api
verdict: jsonb filters, where serializable cannot: is, is_not, contains, not_contains, values always hashes. Note.meta stores what you send but is create-only, so nothing written there is ever editable.
---

# jsonb

**Data type** `jsonb`, probed on `Note.meta` (create-only, project scoped) and
`EventLogEntry.audit_trail` (read only, site-wide audit log). A sweep of `/schema/<Type>/fields` over the
114 entity types in `/schema` found these two and no others. Both declare `editable: false`; only
`Note.meta` honours that on update and not on create. `properties` holds `default_value` (null) and
`summary_default` for both.

**Read** A decoded JSON object or array under `attributes`, never a string holding JSON, never under
`relationships`. Same shape as `serializable`.

`EventLogEntry.audit_trail` is dropped from the response even when named in `fields`: the request 200s and
the key is absent, so the value cannot be read over REST at all.

```
POST /entity/event_log_entries/_search  {"fields": ["audit_trail", "event_type"]} -> 200
 {"type":"EventLogEntry","attributes":{"event_type":"Shotgun_User_PasswordChange"},
  "relationships":{},"id":<id>,"links":{"self":"/api/v1/entity/event_log_entries/<id>"}}
```

**Write** `POST /entity/notes` only. `PUT` on any Note, whatever the value, is refused:

```
"API update() Note.meta is editable on create only."   400 code 103, source {}
```

Sent on create, and read back from the row:

| sent | status | stored |
|---|---|---|
| `{"a": {"b": [1,2,3]}, "c": true, "d": null}` | 201 | identical |
| `[{"x": 1}, {"y": 2}]`, `[1, "two", null, true]` | 201 | identical |
| `{}`, `[]`, `null` | 201 | identical |
| `{"clé": "café 日本語 ✓"}` | 201 | identical |
| `42`, `2.5`, `true`, `"hello"`, `'{"a": 1}'`, `""` | 400 code 103, wrong class | n/a |

```
"API create() Note.meta expected [Hash,\n ActiveSupport::HashWithIndifferentAccess,\n
 ActionDispatch::Http::Parameters,\n ActionDispatch::Http::ParamsHashWithIndifferentAccess,\n
 Array,\n NilClass] data type(s) but got String: \"{\\\"a\\\": 1}\""
```

Any hash or array is taken; there is no structure to satisfy. What is written is what reads back, unlike
`serializable`, where `Task.splits` answers 200 and stores `null`.

**Round trip** Values survive. Object key order does not.

| sent | read back |
|---|---|
| `{"z":1,"a":2,"m_float_whole":1.0,"f":2.5,"big":1099511627776,"t":true,"n":null,"eo":{},"el":[],"es":"","zero":0}` | `{"a":2,"f":2.5,"n":null,"t":true,"z":1,"el":[],"eo":{},"es":"","big":1099511627776,"zero":0,"m_float_whole":1.0}` |

Keys come back ordered by length, then bytewise. `1.0` stays a float, `2**40` stays an integer, `{}`, `[]`,
`""` and `null` all survive, and unicode keys and values round trip unchanged.

**Clear** No path exists on an existing row: every `PUT` is the create-only 400 above, and the stored value
is unchanged after each.

| sent | result |
|---|---|
| `null` on create | 201, reads back `null` |
| `{}` on create | 201, reads back `{}`, distinct from `null` under `is` |
| `[]` on create | 201, reads back `[]` |
| `""` on create | 400 code 103, wrong class |
| `null`, `{}`, `[]`, `""` on update | 400, `Note.meta is editable on create only.` |

**Filter** The type answers with a list, so it is filterable.

```
[["meta", "definitely_not_an_operator", null]] -> 400
 {"status": 400, "code": 103,
  "title": "API read() Note.meta's 'jsonb' data type doesn't support
            'definitely_not_an_operator' 'relation'",
  "source": {"Note.meta": " ... Valid relations: [\"is\",\"is_not\",\"contains\",\"not_contains\"]"}}
```

| operator | value shape | matches |
|---|---|---|
| `is` | a hash or array, or `null` | whole-value equality; key order in the filter is irrelevant |
| `is_not` | same | every other row, `null` rows included |
| `contains` | a hash | containment: `{"a":{"b":[1]}}` matches a stored `{"a":{"b":[1,2,3]}}` |
| `contains` | `{}` | every row holding an object; array and `null` rows do not match |
| `not_contains` | a hash | every other row, `null` rows included |

| filter | result |
|---|---|
| `is {"a":{"b":[1,2,3]}}` against a stored value with two more keys | 0 rows, not a subset match |
| `contains {"m_float_whole": 1}` against a stored `1.0` | 1 row, the number is not type-checked |
| `contains {"x": 1}` or `contains [{"x": 1}]` against a stored `[{"x":1},{"y":2}]` | 0 rows |
| `is [[]]` | the `null` rows, never the row storing `[]` |
| `is ""`, `contains "x"` | 400 code 103, wrong class, the same accepted-class list |
| `contains null` | 400 `'contains' 'relation' expects a non-null value: [nil]` |
| `is []` | 400 `'is' 'relation' expects a 1-element array: []` |
| `in`, `not_in` | 400, the `Valid relations` list |
| any operator on `EventLogEntry.audit_trail` | 200 and no narrowing at all |

**Traps**
- **The filter on `EventLogEntry.audit_trail` is a silent no-op.** `is null` and `is_not null` each return
  the full unfiltered page, so the two together over-count every row. The field is filterable per the
  schema, absent from every response, and ignored in every `WHERE`.
- **`Note.meta` is a one-shot slot.** A client can seed it at create and never revise it, and there is no
  update or clear. `editable: false` in the schema does not predict the create path; a create-time write
  succeeds where every later one 400s.
- **A one-element filter array is unwrapped.** `is [[]]` reaches the field as `[]`, which matches `null`
  rows, so a stored empty array cannot be selected. `contains [{"x": 1}]` is unwrapped to the hash and then
  fails to match an array-valued row.
- **`contains` reaches into objects only.** A stored array is unmatchable by any containment value: a hash
  finds nothing and an array is unwrapped first.
- **Distinct from `serializable` on every axis but read.** `serializable` has no `Valid relations` list and
  cannot be filtered; `Task.splits` accepts a write at 200 and stores `null`. `jsonb` filters with four
  operators and stores exactly what it is given. Both return a decoded value under `attributes`.
