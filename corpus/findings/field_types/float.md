---
tags: [error-handling, silent]
scope: api
measured: first sample project read, 3 rows written in the sandbox project
summary: A decimal number.
verdict: A float reads back as a JSON string rounded to 6 decimals and rejects Integer on both write and filter: send 1.0 or "1.0", never 1; 0.0 and null stay distinct, and 1e-9 silently becomes 0.0.
---

# float

**Data type** `float`, probed on `Version.sg_movie_aspect_ratio` (stock, editable); same on
`Version.sg_frames_aspect_ratio` and `Version.uploaded_movie_duration`. The schema exposes no precision
knob: `properties` is `{"default_value": null, "summary_default": "none"}`.

**Read** Returned under `attributes` as a JSON string, never a JSON number, always with a decimal point,
always rounded to 6 decimal places.

| field | data type | returned |
|---|---|---|
| `uploaded_movie_duration` | `float` | `"0.04"` |
| `sg_uploaded_movie_frame_rate` | `float` | `"25.0"` |
| `frame_count` | `number` | `2` (bare JSON integer) |

**Write** `PUT /entity/versions/<id>` accepts a Float and a numeric String. The rejection names
`[String, BigDecimal, Float, NilClass]`, but no JSON body reaches BigDecimal: a raw literal of
`1.00000000000000000000000000000000000001` is accepted at 200 and reads back `"1.0"`, as a Float would.

| sent | status | read back raw |
|---|---|---|
| `2.5` | 200 | `"2.5"` |
| `-1.5` | 200 | `"-1.5"` |
| `'3.75'` | 200 | `"3.75"` |
| `' 4.5 '` | 200 | `"4.5"`; whitespace trimmed |
| `1.23456789012345` | 200 | `"1.234568"`; 6 dp, rounded not truncated |
| `1.2345678901234567` | 200 | `"1.234568"`; same stored value, indistinguishable |
| `123456789.12345679` | 200 | `"123456789.123457"` |
| `1e+20` | 200 | `"100000000000000000000.0"` |
| `1e-09` | 200 | `"0.0"`; underflow to zero |
| `2` | 400 | `API update() Version.sg_movie_aspect_ratio expected [String, BigDecimal, Float, NilClass] data type(s) but got Integer: 2` |
| `True` | 400 | `...but got TrueClass: true` |
| `'abc'` | 400 | `Invalid data for 'float' data type. Value: abc` |
| `''` | 400 | `Invalid data for 'float' data type. Value: ` |

The rounding is on write, not on read. Three rows set to `1.0000004` each read `"1.0"`, and a
`_summarize` `sum` over them (`probe 020`) returns `3.0`, not the `3.0000012` a store keeping the
seventh decimal would total. A control sum of three rows holding `1.0` returns the same `3.0`.

Control, the same inputs into stock `number` `Version.frame_count` on the same row:

| sent | status | read back raw |
|---|---|---|
| `2` | 200 | `2` |
| `'3'` | 200 | `3` |
| `2.5` | 400 | `API update() Version.frame_count expected [String, Integer, NilClass] ... but got Float: 2.5` |

**Clear** Three sandbox rows: `_a`=0.0, `_b`=null, `_c`=1.0.

| sent | status | read back | filter |
|---|---|---|---|
| `null` | 200 | `null` | `is None` -> 1 (`_b`), `is_not None` -> 2 |
| `0.0` | 200 | `"0.0"` | `is 0.0` -> 1 (`_a`) |
| `''` | 400 | `Invalid data for 'float' data type. Value: ` | n/a |

Only JSON `null` clears; `0.0` is a real value and the two never collapse.

**Filter** The 400 from a bogus relation, `source` verbatim:

```
API read() Version.sg_movie_aspect_ratio's 'float' data type doesn't support
'definitely_not_an_operator' 'relation'. Value: {"path" => "sg_movie_aspect_ratio",
"relation" => "definitely_not_an_operator", "values" => [nil]}
Valid relations: ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
```

The same probe against `Version.frame_count` returns the same seven relations. The vocabulary does not
distinguish `float` from `number`; the accepted value does.

Value shapes, over the three rows above:

| operator | value | matches |
|---|---|---|
| `is` | `1.0` (Float) | 1 |
| `is` | `'1.0'` (String) | 1 |
| `is` | `0.0` | 1 |
| `is` | `None` | 1 |
| `is_not` | `None` | 2 |
| `greater_than` | `0.0` | 1 |
| `less_than` | `2.0` | 2 |
| `between` | `[0.0, 2.0]` | 2 |
| `in` | `[1.0, 0.0]` | 2 |
| `not_in` | `[1.0]` | 2; includes the null row, unlike `SQL NOT IN` |
| `is` | `99999.5` | 0 |
| `in` | `[99999.5]` | 0 |
| `greater_than` | `1e9` | 0 |
| `is` | `1` (Integer) | 400 `API read() ... expected [String, BigDecimal, Float, NilClass] data type(s) but got Integer: 1` |
| `greater_than` | `0` (Integer) | 400, same error |
| `in` | `[1]` (Integer) | 400, same error |

Equality is usable: the comparison rounds to the same 6 decimals the store does.

| `_c` written | reads | `is` value | matches |
|---|---|---|---|
| `1.23456789012345` | `"1.234568"` | `1.23456789012345` | 1 |
| | | `1.234568` | 1 |
| | | `1.2345678901` | 1 |
| | | `1.23` | 0 |
| `1.5` | `"1.5"` | `1.5` | 1 |
| | | `1.5000004` | 1 |
| | | `1.500001` | 0 |
| | | `1.4999999` | 1 |

**Traps**
- Integer is rejected on both halves: `PUT {"field": 1}` and `["field", "is", 1]`. A client that computed
  an aspect ratio as exactly `2` must send `2.0` or `"2.0"`. `number` is the mirror image; it rejects Float.
- The value is a string, so `row["attributes"][f] > 1.0` raises and `== 1.0` is False. Cast on read.
- Precision is 6 decimal places, applied on write, at 200 and without warning. `1e-9` stores as `0.0` and
  then matches `is 0.0`, not `is None`.
- `not_in` returns rows whose value is null, so it is not the complement of `in`. Intersect it with
  `is_not None` for "has a value, but not that one".
