---
tags: [colour]
scope: api
measured: first sample project read, Tasks written only in the sandbox project
summary: A display colour, held as a decimal red, green, blue triple.
verdict: `Task.color` holds the token `pipeline_step` rather than a colour: read `step.Step.color` in the same dotted call and keep a client default. A real value is decimal r,g,b, never hex.
---

# color

**Data type** `color`. Probed on `Task.color` (stock, editable; written only in the sandbox project);
`Step.color` and `Project.color` are read here and never written. Those three are the only `color` fields
on the site, and a custom one is impossible: `POST /schema/<Type>/fields` with `"data_type": "color"`
returns `400 {"data_type": ["data_type is not valid"]}` (probe 019). All three report `mandatory: false`
and the same two properties, no vocabulary: `default_value` (null) and `summary_default` (`'none'`).
Nothing in the schema tells the three apart.

| field | display name | shape | this site | rows `is null` | malformed `is` value |
|---|---|---|---|---|---|
| `Task.color` | `Gantt Bar Color` | `pipeline_step`, or `r,g,b` | `pipeline_step` on all 7445 tasks | 0 | 0 rows |
| `Step.color` | `Color` | `r,g,b` | 23 distinct triples over 35 steps, no nulls | 0 | 400 |
| `Project.color` | `Color` | `r,g,b`, or null | 20 of 52 set, 32 null | 32 | 400 |

**Read** A bare string in `attributes`, never in `relationships`. `pipeline_step` is a sentinel meaning
"render this Task with the colour of its Pipeline Step"; resolve it with a dotted path in the same call
(probe 003), not a second fetch, and keep a client default for a Task whose `step` resolves to nothing.

```
GET /entity/tasks?fields=color,step.Step.color
  {"color": "pipeline_step", "step.Step.color": "253,94,99"}
```

**Write** `PUT /entity/tasks/<id>` with a string; legacy names are case-insensitive and stored expanded.

| sent | result |
|---|---|
| `"255,128,0"`, `"pipeline_step"` | 200, reads back verbatim |
| `"Blue"`, `"Orange"` | 200, stored `2,149,216` and `253,141,3` |
| `"Pink"`, `"Red"` / `"red"` | 200, stored `254,125,179` and `253,1,0` |
| `"Green"`, `"Purple"` | 200, stored `29,215,46` and `183,0,188` |
| `"Grey"`, `"Black"` | 200, stored `129,129,129` and `45,45,45` |
| key omitted on create | reads `pipeline_step`; the schema's `default_value: null` is wrong |
| `"#ff8000"`, `"ff8000"`, `"Gray"`, `"White"`, `"Cyan"` | 400 `Value is not a valid color token` |
| `"255, 128, 0"` (spaces), `"-1,0,0"`, `"255.0,128.0,0.0"` | 400 `At least one component value is not valid` |
| `"300,0,0"` | 400 `At least one component value is out of range` |
| `"255,128"`, `"255,128,0,255"` | 400 `The value is not a valid color expression` |
| `[255, 128, 0]` | 400 `expected [String, NilClass] data type(s) but got Array` |
| `16744448` | 400 `expected [String, NilClass] data type(s) but got Integer` |
| `"#ff8000"` on `POST /entity/tasks` | 400, the whole create fails and no row is made |

Each of those 400s appends the same grammar, the authoritative spec for the type:
```
"Update failed for [Task.color]:  (task.rb) Value is not a valid color token: [#ff8000]Unsupported
 format for Task color field. The Task color can not be nil, the expected format is r,g,b where the
 values of r,g and b are in the range 0-255. The value of the color can also be set using the legacy
 color strings which are; Blue, Orange, Pink, Red, Green, Purple, Grey and Black. ..."
```

**Clear** `Task.color` cannot be cleared; write `pipeline_step` to un-set it.

| sent | result |
|---|---|
| `null` | 400 `Value cannot be nil for Task.color.`, value unchanged |
| `""` | 400 `The value is not a valid color expression: []`, value unchanged |

After the `""` attempt, `[["id","is",<id>],["color","is",null]]` still matches 0 rows. The refusal comes
from the field, not the schema: `mandatory: false`, and the type layer accepts `NilClass`. A written null
was tried on `Task` alone, `Step` and `Project` rows being site-wide, so nullability on those two is a
read-side count and nothing more: 32 Projects hold null, no Step does.

**Filter** Four relations, byte-identical to `list` and `status_list`; `contains`, `not_contains`,
`starts_with` and `ends_with` all 400 with the same body:

```
[["color", "definitely_not_an_operator", null]] -> 400
 title:  "API summarize() Task.color's 'color' data type doesn't support
          'definitely_not_an_operator' 'relation'"
 source: {"Task.color": " data type doesn't support 'definitely_not_an_operator' 'relation'. Value:
    {"path" => "color", "relation" => "definitely_not_an_operator", "values" => [nil]}
    Valid relations: ["is", "is_not", "in", "not_in"]"}
```

The value is the stored string, counted over 1900 `Task` rows:

| operator | value | matches |
|---|---|---|
| `is` | `"pipeline_step"` | 1900 of 1900, the stored keyword |
| `is` | `"PIPELINE_STEP"` | 0; the value is case-sensitive |
| `is` | `"0,126,174"` | 0; no `Task` stores a triple |
| `is` | `[0, 126, 174]` | 400 `'is' 'relation' expects a 1-element array: [0, 126, 174]` |
| `is_not` | `"pipeline_step"` | 0 |
| `is_not` | `null` | 1900, every row holds a value |
| `in` | `"pipeline_step"` (bare, outside a list) | accepted, a scalar where a list is expected |
| `in` | `["zzprobe_nope"]` | 0, the negative control |
| `not_in` | `["pipeline_step"]` | 0 |

`Step`, 35 rows, and `Project`, 52 rows, reject the keyword form outright and take the triple:

| `is <value>` | Step | Project |
|---|---|---|
| `"pipeline_step"`, `"PIPELINE_STEP"` | 400 invalid format | 400 invalid format |
| `"0,126,174"` | 1 | 0 |

A malformed value 400s on `Step` and `Project` and returns 0 rows on `Task`:
```
400 "API summarize() invalid format for color value: "#ff8000" Correct format is '127,127,127' with
     values from 0 to 255 inclusive."   same for "255, 128, 0", "red", "255,128"; "300,0,0" gives
     "invalid range in color value"
```

**Traps**
- Never treat `Task.color` as a colour. A swatch renderer parsing it as `r,g,b` gets `pipeline_step` on
  every row this site has and must follow `step.Step.color` instead.
- Decimal `r,g,b`, no spaces and no `#`, matching `Status.bg_color` (probe 010). Hex is rejected on write
  and on filter. Build it with `"%d,%d,%d" % rgb`, split on `,` to read.
- No `Task.color` row on this site is empty and a written null is refused, so a fill-rate count over it
  reads 100% and measures nothing (probe 007).
- A bad filter value is a 400 on `Step` and `Project` but a silent 0 rows on `Task`.
- Writing a legacy name is lossy: `"Red"` stores `253,1,0` and never reads back as `"Red"`, so filtering
  on the name it was written with returns 0.

**Python equivalent**

```python
sg.update("Task", tid, {"color": "255,128,0"})       # decimal triple, no spaces
sg.update("Task", tid, {"color": "pipeline_step"})   # the only way to un-set it; None is a 400
t = sg.find_one("Task", [["id", "is", tid]], ["color", "step.Step.color"])
c = t["step.Step.color"] if t["color"] == "pipeline_step" else t["color"]
rgb = tuple(int(x) for x in c.split(",")) if c else None
```
