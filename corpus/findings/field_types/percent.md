---
tags: [field-type, percent, number, write, filter, operator, fill-rate, trap]
scope: api
summary: A percentage, held as a whole number on a 0 to 100 scale.
verdict: A percent is a bare integer on a 0-100 scale (50% is 50, and 0.5 is rejected as Float), but nothing is clamped, so -1, 1000 and 2**31-1 all store at HTTP 200.
---

# percent

**Data type** `percent`, probed on `Shot.sg_vendor_percentage_complete` (stock, editable). Same on
`Shot.sg___complete`. The schema declares neither a range nor a scale: `properties` is only
`{"default_value": null, "summary_default": "none"}`.

**Read** A bare JSON integer under `attributes` on a 0-100 scale: 50% is `50`, not a string, not a
fraction, no `%` sign. An unset field reads `null`, not `0` and not absent.

```
{"sg_vendor_percentage_complete":50}
a Shot created without the field ever set reads null
```

**Against `number` and `float`**

| type | accepted on write | read shape | operators |
|---|---|---|---|
| `percent` | `[Integer, NilClass]` | bare integer | `is, is_not, greater_than, less_than, between, in, not_in` |
| `number` | `[String, Integer, NilClass]`, coerces `"42"` | bare integer | the same list, word for word |
| `float` | rejects the `Integer` `percent` demands | quoted string | the same list, word for word |

**Write** `PUT /entity/shots/<id>` with a bare `{"sg_vendor_percentage_complete": 42}`;
`POST /entity/shots` takes the same value shape and 201s. Every rejection names the accepted set:
`[Integer, NilClass]`, the narrowest of the three numeric types.

| sent | result |
|---|---|
| `42` | 200, reads `42` |
| `1` | 200, reads `1` |
| `50` | 200, reads `50` |
| `100` | 200, reads `100` |
| `101` | 200, reads `101` |
| `-1` | 200, reads `-1` |
| `-1000` | 200, reads `-1000` |
| `1000` | 200, reads `1000` |
| `1000000` | 200, reads `1000000` |
| `2147483647` | 200, reads `2147483647` |
| `2147483648`, `PUT` | 400 `{"status": 400, "code": 104, "source": null, "title": "Update failed for [Shot.sg_vendor_percentage_complete]: Invalid statement."}` |
| `2147483648`, `POST` | 400 `{"status": 400, "code": 104, "source": null, "title": "Create failed for [Shot]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n", "meta": {"crud_error_uuid": "<uuid>"}}` |
| `0.5` | 400 `API update() Shot.sg_vendor_percentage_complete expected [Integer, NilClass] data type(s) but got Float: 0.5` |
| `42.5` | 400 `... but got Float: 42.5` |
| `0.001` | 400 `... but got Float: 0.001`; no rounding, no truncation |
| `'42'` | 400 `... but got String: "42"` |
| `' 42 '` | 400 `... but got String: " 42 "` |
| `'50%'` | 400 `... but got String: "50%"` |
| `'abc'` | 400 `... but got String: "abc"` |
| `''` | 400 `... but got String: ""` |
| `True` | 400 `... but got TrueClass: true` |
| `'50%'`, `POST` | 400 `API create() Shot.sg_vendor_percentage_complete expected [Integer, NilClass] data type(s) but got String: "50%"` |

The only ceiling is the signed 32-bit one the `number` finding records, and the two verbs fail
differently there in the same way.

**Clear**

| sent | result |
|---|---|
| `null` | 200, reads `null` |
| `0` | 200, reads `0`: a value, not a clear |
| `""` | 400, rejected as `String` |

`0` and `null` stay distinct on write, on read and under a filter: `is 0` matched 1 row, `is None`
matched 2: the row set to `null` and the row never set.

**Filter** `POST /entity/shots/_search`, `Content-Type: application/vnd+shotgun.api3_array+json`.
A bogus relation 400s with the whole vocabulary (`probe 017`):

```
Valid relations: ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
```

`contains`, `starts_with` and `not_between` are absent, and each 400s with that same list. There is no
`>=` or `<=`. Bracket with `between`, or shift the bound by one.

Match counts over 5 sandbox rows holding `0`, `null`, `50`, `50`, `null`:

| operator | value | matches |
|---|---|---|
| `is` | `50` | 2 |
| `is` | `0` | 1 |
| `is` | `null` | 2 |
| `is` | `99999` | 0 |
| `is_not` | `50` | 3 |
| `is_not` | `null` | 3 |
| `in` | `[50, 0]` | 3 |
| `in` | `[99999]` | 0 |
| `not_in` | `[50]` | 3 |
| `greater_than` | `0` | 2 |
| `greater_than` | `-1` | 3 |
| `less_than` | `1` | 1 |
| `less_than` | `100` | 3 |
| `between` | `[0, 100]` | 3 |
| `between` | `[200, 300]` | 0 |

Rejected filter values:

| sent | result |
|---|---|
| `is 50.0` | 400 `API read() Shot.sg_vendor_percentage_complete expected [Integer, NilClass] data type(s) but got Float: 50.0` |
| `is 0.5` | 400, the same `[Integer, NilClass]` rejection |
| `is '50'` | 400, the same `[Integer, NilClass]` rejection |
| `between [0, 0.9]` | 400, the same `[Integer, NilClass]` rejection |
| `between 50` | 400 `API read() 'between' 'relation' expects a 2-element array: [50]` |
| `contains '5'` | 400 `... 'percent' data type doesn't support 'contains' 'relation'` |

**Traps**
- **Integer or nothing, on both halves.** `PUT {"field": "50"}` and `["field", "is", "50"]` each 400
  with `expected [Integer, NilClass] ... but got String`. `int()` a value out of a CSV or a form field
  before sending it.
- **The 0-100 range is a convention, not a constraint.** `-1`, `101` and `1000000` all store at 200 and
  read back unchanged, and no `properties` key declares a bound. Validate before writing, and clamp on
  read; a percent field is not evidence that its value is a fraction of a whole.
- **`0` is a value and `""` is not a clear.** Following `probe 007`, a row holding `0` is `is_not None`,
  so a percent field full of zeroes scans as 100% filled. Rank by `greater_than 0`, never by fill rate.
- **Negation includes nulls; comparison excludes them.** `is_not 50` and `not_in [50]` return the null
  rows too, 3 of 5; `greater_than -1` returns only the 3 rows holding a value. A "not yet at 100%"
  filter written as `is_not 100` sweeps in every unset row.
