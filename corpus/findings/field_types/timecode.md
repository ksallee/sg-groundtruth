---
tags: [field-type, timecode, number, media, write, filter, operator, schema, summary, trap]
scope: api
summary: A position in a timeline.
verdict: A timecode stores milliseconds as a signed 32-bit integer. No schema or preference names its frame rate, but a _summarize group_name renders `HH:MM:SS:FF` and the rate solves out of that.
---

# timecode

**Data type** `timecode`, probed on `Sequence.sg_timecode` (stock, editable). A sweep of
`/schema/<Type>/fields` over all 114 entity types finds it on exactly one field site-wide; every other
field named for timecode is a different data type:

| field | data_type |
|---|---|
| `Cut.timecode_start_text`, `Cut.timecode_end_text` | `text` |
| `CutItem.timecode_edit_in_text`, `_edit_out_text`, `_cut_item_in_text`, `_cut_item_out_text` | `text` |
| `SourceClip.sg_tc_start`, `SourceClip.sg_tc_end` | `text` |
| `SourceClip.sg_tc_framerate` | `number` |

**Read** A plain JSON integer under `attributes`, never a string and never wrapped. An unset field is
`null`, not `0` and not absent: `{"code": "seq01", "sg_timecode": null}`. No read path renders it:
`GET`, `_search`, a dotted read from a linked Shot and `_summarize` `sum` all return the same integer.

**Unit and frame rate** The integer is milliseconds. Four routes to the rate, three dead:

| route | result |
|---|---|
| `GET /schema/Sequence/fields/sg_timecode` | `properties` holds `default_value` and `summary_default`, nothing else |
| `GET /preferences` | 200, 17 keys including `hours_per_day` and `duration_units`, none about frames or rate; `/entity/preferences`, `/settings`, `/entity/settings` and `/schema/Preference/fields` all 404 |
| rate fields on other entity types | `Cut.fps` empty, `Slate.sg_fps` and `SourceClip.sg_tc_framerate` hold `24`, `Version.sg_uploaded_movie_frame_rate` holds `"25.0"`; none is linked to Sequence |

Grouping is the one place the server states its units, as `field_types/calculated` found for
`duration`: `_summarize` with `"grouping": [{"field": "sg_timecode", "type": "exact"}]` returns
`group_value`, the raw integer, beside `group_name`, the server's own render.

| group_value | group_name | group_value | group_name |
|---|---|---|---|
| `1` | `00:00:00:00` | `981` | `00:00:01:00` |
| `20` / `21` | `00:00:00:00` / `00:00:00:01` | `1000` | `00:00:01:00` |
| `500` | `00:00:00:12` | `3600000` | `01:00:00:00` |
| `813` / `814` | `00:00:00:19` / `00:00:00:20` | `86400000` | `24:00:00:00` |
| `980` | `00:00:00:23` | `2147483647` | `596:31:23:16` |

`1000` renders as one whole second, which fixes the unit. The frame digits are the sub-second
remainder rounded to the nearest frame, so each step brackets the rate: the 19.5-frame step falls in
`(813, 814]`, giving fps in `[23.9558, 23.9852)`, the 23.5-frame step in `(980, 981]`, giving
`[23.9551, 23.9796)`. The intersection holds `24000/1001 = 23.976` and excludes 24, 25 and 30.

**Write** `PUT /entity/sequences/<id>` with `Content-Type: application/json` and a bare
`{"sg_timecode": 3600000}`; `POST` takes the same shape. The rejection states the accepted set,
`[Integer, NilClass]`: the narrowest of the numeric types, and no string coerces.

| sent | result |
|---|---|
| `3600000`, `1`, `0` | 200, reads back unchanged |
| `-1`, `-3600000` | 200, reads back unchanged; negatives are stored |
| `86400000`, `86400001` | 200, reads back unchanged; nothing wraps at 24 hours |
| `null` | 200, reads back `null` |
| `2147483647` (`2**31-1`), `-2147483648` (`-(2**31)`) | 200, exact |
| `"01:00:00:00"` | 400 `API update() Sequence.sg_timecode expected [Integer, NilClass] data type(s) but got String: "01:00:00:00"` |
| `"01:00:00;00"` (drop frame), `"01:00:00"`, `"banana"` | 400, same message with the sent string |
| `"3600000"` | 400, same message with `"3600000"` |
| `1.5` | 400 `... but got Float: 1.5`; no truncation |
| `true` | 400 `... but got TrueClass: true` |
| `2147483648`, `-2147483649` | 400 |

**Range** A signed 32-bit integer, and the two verbs fail differently at the ceiling:

| verb | body |
|---|---|
| `PUT` | `{"status": 400, "code": 104, "title": "Update failed for [Sequence.sg_timecode]: Invalid statement.", "source": null, "detail": null, "meta": null}` |
| `POST` | `{"status": 400, "code": 104, "title": "Create failed for [Sequence]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n", "source": null, "detail": null, "meta": {"crud_error_uuid": "<uuid>"}}` |

**Clear**

| sent | result |
|---|---|
| `null` | 200, reads back `null` |
| `0` | 200, reads back `0`; a value, not a clear |
| `""` | 400 `expected [Integer, NilClass] data type(s) but got String: ""`; the old value survives |
| field omitted from the create | reads `null` |

**Filter** `POST /entity/sequences/_search`,
`Content-Type: application/vnd+shotgun.api3_array+json`. This type answers a bogus relation with the
whole vocabulary (`probe 017`), the same seven `number` and `duration` return:

```
Valid relations: ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
```

There is no `>=` or `<=`; bracket with `between`. Against 4 rows holding `3600000`, `0`, `null`, `null`:

| operator | value | matches |
|---|---|---|
| `is` | `3600000` | 1 |
| `is` | `0` | 1 |
| `is` | `None` | 2; the row holding `0` is not matched |
| `is` | `"01:00:00:00"` | 400 `expected [Integer, NilClass] data type(s) but got String: "01:00:00:00"` |
| `is` | `"3600000"`, `3600000.0` | 400, the same message with `String: "3600000"` and `Float: 3600000.0` |
| `is_not` | `3600000` | 3 |
| `is_not` | `None` | 2 |
| `greater_than` | `0` | 1 |
| `greater_than` | `3600000` | 0 |
| `greater_than` | `-1` | 2 |
| `less_than` | `3600000` | 1 |
| `less_than` | `1` | 1 |
| `between` | `[0, 7200000]` | 2 |
| `between` | `[7200000, 9000000]` | 0 |
| `between` | `3600000` | 400 `API read() 'between' 'relation' expects a 2-element array: [3600000]` |
| `in` | `[3600000, 0]` | 2 |
| `in` | `[999999999]` | 0 |
| `in` | `["3600000"]` | 400 `expected [Integer, NilClass] data type(s) but got String: "3600000"` |
| `not_in` | `[3600000]` | 3 |
| `not_in` | `[999999999]` | 4 |
| `contains` | `"3600"` | 400 `API read() Sequence.sg_timecode's 'timecode' data type doesn't support 'contains' 'relation'` |
| `starts_with` | `"01"` | 400, the same body |
| `not_between` | `[0, 10]` | 400, the same body |

An unsupported relation repeats the sent filter and the `Valid relations` list under `source`. A type
error, on read or on write, puts the whole message in `title` and leaves `source` empty.

**Traps**
- **The rate is real but hidden.** Solve it once per site from two `_summarize` writes and store it;
  a client that guesses 24 or 25 is wrong by a frame inside the first second.
- **A timecode field rejects timecode strings.** `"01:00:00:00"` and the drop-frame `"01:00:00;00"`
  both 400 on write and again inside a filter, and a numeric string does not coerce the way it does for
  `number` and `duration`. Send `int` milliseconds.
- **Nothing is validated as a time.** `-3600000`, `86400001` and `2147483647` all store, and render
  as `-1:59:59:00`, `24:00:00:00` and `596:31:23:16`; `-1` renders as `-1:59:60:00`, a 60th second.
  Range-check before writing. The API only enforces the 32-bit column.
- **Negation includes nulls; comparison excludes them.** `is_not 3600000` and `not_in [999999999]`
  return the null rows too (3 and 4 of 4), while `greater_than -1` returns only the 2 rows holding a
  value. A row holding `0` is `is_not None`, so a field full of zeroes scans as fully populated
  (`probe 007`); rank by `greater_than 0`.
- **A new field belongs in `text`, not here.** Every stock field a cut or a source clip uses for
  timecode is `text` plus a `number` rate, which round-trips `HH:MM:SS:FF` and survives drop frame.
