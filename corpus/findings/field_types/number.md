---
tags: [field-type, number, write, filter, operator, fill-rate, trap]
scope: api
verdict: A number is a signed 32-bit integer: floats 400, 2**31 is "integer out of range", and 0 is not null, yet is_not and not_in match null rows while greater_than and less_than do not.
---

# number

**Data type** `number`, probed on `Version.frame_count` and `Version.sg_first_frame` (stock, editable).
Also stock and editable on Version: `sg_last_frame`. The schema declares no range: `properties` holds only
`default_value` (null here) and `summary_default`.

**Read** A plain JSON integer under `attributes`, never a string and never wrapped. An unset field is
`null`, not `0` and not absent.

```
id=<n> sg_first_frame=1001(int) sg_last_frame=1100(int) frame_count=100(int)
```

**Write** `PUT /entity/versions/<id>` with `Content-Type: application/json` and a bare
`{"frame_count": 42}`; `POST /entity/versions` takes the same value shape. The API states its own accepted
set in the rejection: `[String, Integer, NilClass]`.

| sent | result |
|---|---|
| `42` | 200, reads back `42` |
| `'42'` | 200, reads back `42`; coerced to int, no error |
| `-7` | 200, reads back `-7` |
| `null` | 200, reads back `None` |
| `3.7` / `3.2` / `-3.7` | 400 `API update() Version.frame_count expected [String, Integer, NilClass] data type(s) but got Float: 3.7`; no truncation, no rounding |
| `True` | 400 `... but got TrueClass: true` |
| `'42abc'` | 400 title `Invalid data for 'number' data type`; source `{"frame_count": "Invalid data for 'number' data type. Value: 42abc"}` |
| `''` | 400 source `{"frame_count": "Invalid data for 'number' data type. Value: "}` |

**Range** A signed 32-bit integer.

| sent | result |
|---|---|
| `2147483647` (`2**31-1`) | 200, reads back exactly |
| `2147483648` (`2**31`) | 400 |
| `4294967295` / `2**63-1` / `2**63` | 400 |
| `-2147483648` (`-(2**31)`) | 200, reads back exactly |
| `-2147483649` | 400 |
| `-(2**63)` | 400 |
| `"2147483648"` as a numeric string | 400; a string does not route around the ceiling |

The two verbs fail differently on `2147483648`:

| verb | body |
|---|---|
| `PUT` | `{"status": 400, "code": 104, "title": "Update failed for [Version.frame_count]: Invalid statement.", "source": null, "detail": null, "meta": null}` |
| `POST` | `{"status": 400, "code": 104, "title": "Create failed for [Version]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n", "source": null, "detail": null, "meta": {"crud_error_uuid": "<uuid>"}}` |

**Clear**

| sent | result |
|---|---|
| `null` | 200, reads back `None` |
| `0` | 200, reads back `0` |
| `''` | 400 `Invalid data for 'number' data type. Value: ` |
| field never set on create | reads `None` |

`null` clears; `0` is a value. They are distinct on write, on read and under a filter.

**Filter** `POST /entity/versions/_search`, `Content-Type: application/vnd+shotgun.api3_array+json`.
A bogus relation 400s with the whole vocabulary (`probe 017`):

```
Valid relations: ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
```

`contains`, `starts_with`, `ends_with` and `not_between` are all absent, and each 400s with that same list.
There is no `>=` or `<=`. Bracket with `between`, or shift the bound by one.

Match counts are against 4 sandbox rows holding `1001`, `0`, `null`, `null`.

| operator | value shape | matches |
|---|---|---|
| `is` | `1001` | 1 |
| `is` | `0` | 1 |
| `is` | `'1001'` | 1 |
| `is` | `None` | 2; `0` is not matched |
| `is_not` | `1001` | 3 |
| `is_not` | `None` | 2 |
| `greater_than` | `0` | 1 |
| `greater_than` | `-1` | 2 |
| `less_than` | `1` | 1 |
| `less_than` | `1001` | 1 |
| `in` | `[1001, 0]` | 2 |
| `in` | `['1001']` | 1 |
| `in` | `[999999]` | 0 (negative control) |
| `not_in` | `[1001]` | 3 |
| `not_in` | `[999999]` | 4 |
| `between` | `[0, 2000]` | 2 |
| `between` | `[2000, 3000]` | 0 (negative control) |
| `between` | `1001` | 400 `API read() 'between' 'relation' expects a 2-element array: [1001]` |
| `contains` | `'100'` | 400 `API read() Version.sg_first_frame's 'number' data type doesn't support 'contains' 'relation'`; source repeats the `Valid relations` list |

**Traps**
- **Signed 32-bit, not 64.** A 64-bit id or seed reaches `2**64-1` and must be stored in a `text` field
  (`probe 019` saw the same ceiling on a created field). The create path names the cause,
  `PG::NumericValueOutOfRange`; the update path says only `Invalid statement.`
- **A float is rejected, not coerced.** `int()` anything computed (a mean, a ratio, `n/2` in Python 3)
  before writing it. A numeric string coerces, so `"42"` works and `42.0` does not.
- **`0` is a value, `''` is not a clear.** `null` is the only clear. Following `probe 007`: a row holding
  `0` is `is_not None`, so a number field full of zeroes scans as 100% filled, exactly like a checkbox
  full of `False`. Rank a number field by `greater_than 0`, or by `_summarize` grouping (`probe 020`),
  never by fill rate.
- **Negation includes nulls; comparison excludes them.** `is_not 1001` and `not_in [999999]` return the
  null rows too (3 and 4 of 4), while `greater_than -1` returns only the 2 rows that hold a value. Any
  "everything except X" filter over a sparse number field silently sweeps in every unset row.
