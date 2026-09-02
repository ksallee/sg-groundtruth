---
tags: [field-type, duration, number, write, filter, operator, schema, trap]
scope: api
measured: first sample project, 500 Tasks; 4 rows written in the sandbox project
summary: A length of time, stored as a whole number of minutes.
verdict: A duration is a bare integer of minutes and no schema property names the unit, but `GET /preferences` returns `hours_per_day` and `duration_units`, so a client can render hours or days.
---

# duration

**Data type** `duration`, probed on `Shot.sg_bid___total`.

| field | access |
|---|---|
| `Shot.sg_bid___total`, `Shot.sg_bid___ani/___comp/___fx/___lit` | stock, editable |
| `Task.duration`, `Task.est_in_mins`, `TimeLog.duration` | stock, editable |
| `Task.time_logs_sum`, `Task.time_vs_est` | read-only |

**Unit** The stored integer is minutes. The field schema names no unit: `properties` holds
`default_value` and `summary_default` and nothing else.

```
GET /schema/Shot/fields/sg_bid___total
  properties keys: ['default_value', 'summary_default']
  {"default_value": {"value": null, "editable": false},
   "summary_default": {"value": "none", "editable": true}}
Task/fields/duration      properties={"default_value": null, "summary_default": "sum"}
Task/fields/est_in_mins   properties={"default_value": null, "summary_default": "sum"}
TimeLog/fields/duration   properties={"default_value": 0,    "summary_default": "sum"}
```

| evidence | reading |
|---|---|
| the stock field is named `est_in_mins` | the one place the API states a unit |
| `Task.time_logs_sum` 246 = sum of `TimeLog.duration` [180, 66]; 247 = sum of [60, 120, 45, 22] | same unit, plain addition |
| 500 `Task.duration` on demo_show: gcd 600, distinct [0, 600, 1200, … 6000] | 10-hour multiples, not whole days |

`GET /preferences` returns 200 with 17 keys, two of them about durations. On the probed site
`hours_per_day` is `8.0` and `duration_units` is `"days"`: render days as `minutes / (60 * hours_per_day)`.

**Read** A plain JSON integer under `attributes`, never a string and never wrapped. An unset field is
`null`.

```
duration=2400(int) est_in_mins=360(int) time_logs_sum=246(int)
```

**Write** `PUT /entity/shots/<id>` with `Content-Type: application/json` and a bare
`{"sg_bid___total": 90}`; `POST /entity/shots` takes the same value shape. The accepted set is stated in
the rejection: `[String, Integer, NilClass, Float]`, one member wider than `number`.

| sent | result |
|---|---|
| `90`, `1440`, `-30` | 200, reads back unchanged |
| `"90"` | 200, reads back `90` |
| `" 90 "` | 200, reads back `90`; whitespace stripped |
| `null` | 200, reads back `null` |
| `2147483647` (`2**31-1`) | 200, exact |
| `2147483648` | 400 `Update failed for [Shot.sg_bid___total]: Invalid statement.` |
| `1.5` | 200, stored as `1` |
| `90.4`, `90.5`, `90.6`, `90.9` | 200, stored as `90` |
| `-1.5`, `-90.6` | 200, stored as `-1`, `-90` |
| `0.4` | 200, stored as `0`, not `null` |
| `"2:30"`, `"1h"`, `"90m"`, `"1d"`, `""` | 400 `Invalid data for 'duration' data type` |
| `true` | 400 `API update() Shot.sg_bid___total expected [String, Integer, NilClass, Float] data type(s) but got TrueClass: true` |

A Float truncates toward zero, with no rounding.

```
PUT sg_bid___total="2:30" -> 400
 {"status": 400, "code": 103, "title": "Invalid data for 'duration' data type",
  "source": {"sg_bid___total": "Invalid data for 'duration' data type. Value: 2:30"},
  "detail": null, "meta": null}
```

**Clear**

| sent | result |
|---|---|
| `null` | cleared, reads back `None` |
| `0` | 200, stored as `0`; a value, not a clear |
| `""` | 400 `Invalid data for 'duration' data type. Value: `; the old value survives |
| never set | reads `None` |

**Filter** `POST /entity/shots/_search`, `Content-Type: application/vnd+shotgun.api3_array+json`.
A bogus relation 400s with the whole vocabulary (`probe 017`), the same list `number` returns:

```
Valid relations: ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
```

There is no `>=` or `<=`: bracket with `between`, or shift the bound by one.

Against 4 sandbox rows holding `480`, `0`, `null`, `null`:

| operator | value | matches |
|---|---|---|
| `is` | `480` | 1, the row holding it |
| `is` | `"480"`, `480.0`, `480.6` | 1 each, the same row; a string and a float both coerce |
| `is` | `0` | 1 |
| `is` | `None` | 2; the row holding `0` is not matched |
| `is` | `"8:00"` | 400 `Invalid data for 'duration' data type. Value: 8:00` |
| `is_not` | `480` | 3 |
| `is_not` | `None` | 2 |
| `greater_than` | `0` | 1 |
| `greater_than` | `480` | 0 |
| `greater_than` | `-1` | 2 |
| `less_than` | `480` | 1 |
| `less_than` | `1` | 1 |
| `between` | `[0, 600]` | 2 |
| `between` | `[600, 900]` | 0 |
| `between` | `480` | 400 `API read() 'between' 'relation' expects a 2-element array: [480]` |
| `in` | `[480, 0]` | 2 |
| `in` | `["480"]` | 1 |
| `in` | `[999999]` | 0 |
| `not_in` | `[480]` | 3 |
| `not_in` | `[999999]` | 4 |
| `contains` | `"48"` | 400 `API read() Shot.sg_bid___total's 'duration' data type doesn't support 'contains' 'relation'` |
| `not_between` | `[0, 600]` | 400 `API read() Shot.sg_bid___total's 'duration' data type doesn't support 'not_between' 'relation'` |

Each of those two 400s repeats the sent filter and the `Valid relations` list above under `source`.

**Traps**
- **The unit is on the site, not on the field.** No `/schema` route names it. Read `hours_per_day` and
  `duration_units` once from `GET /preferences`, then render.
- **A Float truncates instead of failing.** `number` 400s on `3.7` (`field_types/number`); `duration`
  takes `90.9` and stores `90`. Round before writing an average, a ratio or `total/2`.
- **`"2:30"` is not a duration.** The only string the API accepts is one that parses as a number.
- **Negation includes nulls; comparison excludes them.** `is_not 480` and `not_in [999999]` return the
  null rows too (3 and 4 of 4); `greater_than -1` returns only the 2 rows holding a value. A row holding
  `0` is `is_not None`, so a field full of zeroes scans as fully populated (`probe 007`); rank by
  `greater_than 0`.
