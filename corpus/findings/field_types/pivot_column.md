---
tags: [field-type, pivot-column, step, schema, filter, operator, inspector, trap]
scope: api
measured: first sample project read, sandbox project written
summary: A per-step rollup the web interface draws, with no value over REST.
verdict: A pivot_column is a web-UI task rollup with no REST implementation - it reads null on every row, and write, filter, sort and _summarize each fail with a different error.
---

# pivot_column

**Data type** `pivot_column`, probed on `Shot.step_8` and `Version.step_0` (stock, read-only), every
row below run on both. No `pivot_column` field is editable on any entity type, and none returns data
over REST.

| operation | outcome |
|---|---|
| read | 200, `null` on every row |
| create or update | 400 `API update() Version.step_0 is read only.`, `API update() Shot.step_8 is read only.` |
| clear | 400, same string |
| filter, either relation | 400 code 103 `API read() of data type 'pivot_column' not supported in API` |
| sort, `_search` and `GET` | 400 code 104 `Read failed for entity type [Shot]`, `[Version]` on the other |
| `_summarize`, grouping and count | 500 `Shotgun Server Error` |

`step_<n>` is the rollup of that entity's Tasks whose `step` is Step `n`, and the schema `name.value` is
that Step's `code`. 35 of 35 non-zero fields resolve, with `entity_type` matching the field's type:
`Shot.step_8` -> `GET /entity/steps/8` 200, `code` `stepA`, `entity_type` `Shot`, `name.value` `stepA`.
`step_0` is the all-steps column, not a Step: `name.value` is `ALL TASKS` and
`GET /entity/steps/0` returns 400 `record_id must be greater than 0`.

`properties` holds `{default_value: null, summary_default: "none"}` and nothing else: no source field,
no Step link, no declared result type. What the column pivots on is readable only from the id in the name.

A type gets one `step_<n>` per Step defined for it, plus `step_0`. 45 fields on 10 of 114 types:

| entity type | fields | Steps |
|---|---|---|
| `Asset` | 14 | 13 |
| `Shot` | 13 | 12 |
| `Level` | 11 | 10 |
| `Version`, `Sequence`, `ShootDay`, `Launch`, `MocapSetup`, `MocapTake`, `MocapTakeRange` | 1 (`step_0`) | 0 |

The Steps column is `GET /entity/steps` grouped by `entity_type`, not an inference from the field names:
the site's 35 Steps are `Asset` 13, `Shot` 12 and `Level` 10, and the seven types on the last row appear
in that listing not at all. Adding a Step adds a column, so enumerate, never hardcode one.

**Read** The key is present in `attributes` and always `null`, never under `relationships`. That is
not how an unknown field behaves: a bogus name is dropped silently (probe 004).

| `?fields=` | in the 200 |
|---|---|
| `step_8`, `step_0` | `{"step_8": null, "step_0": null}` |
| `sg_not_a_real_field` | absent |

Null holds where the rollup provably has content. `Shot` `sh010` has a finished Task on each Step:

```
Task 'stepA' step=8  sg_status_list 'fin' on Shot sh010 -> shot.step_8  = None
Task 'stepC' step=7  sg_status_list 'fin' on Shot sh010 -> shot.step_7  = None
Task 'stepD' step=35 sg_status_list 'fin' on Shot sh010 -> shot.step_35 = None
600 newest rows site-wide x every pivot field on the type: 0 non-null cells of 5600
```

**Write** Refused on create and on update, with the field named:

| sent | result |
|---|---|
| `PUT /entity/versions/<id> {"step_0": "fin"}` | 400 `API update() Version.step_0 is read only.` |
| `POST /entity/versions {..., "step_0": "fin"}` | 400 `API create() Version.step_0 is read only.` |
| `PUT /entity/shots/<id> {"step_8": "fin"}` | 400 `API update() Shot.step_8 is read only.` |
| `POST /entity/shots {..., "step_8": "fin"}` | 400 `API create() Shot.step_8 is read only.` |

Nothing is accepted and discarded: the whole request 400s, so a create that includes a pivot column
loses the row it meant to make.

**Clear** There is nothing to clear, and no value is treated differently:

| sent | result |
|---|---|
| `{"step_0": null}` | 400 `API update() Version.step_0 is read only.` |
| `{"step_8": null}` | 400 `API update() Shot.step_8 is read only.` |
| `{"step_0": "fin"}` | 400, same string |
| key omitted | unchanged, reads `null` |

**Filter** The API enumerates two relations and then honours neither:

```
["step_8", "definitely_not_an_operator", null] -> 400
 title:  "API read() Shot.step_8's 'pivot_column' data type doesn't support
          'definitely_not_an_operator' 'relation'"
 source: {"Shot.step_8": " data type doesn't support 'definitely_not_an_operator' 'relation'.
          Value: {"path" => "step_8", "relation" => "definitely_not_an_operator",
          "values" => [nil]} Valid relations: ["is", "is_not"]"}
```

`Valid relations: ["is", "is_not"]` is the generic list the operator validator prints before the type
check runs. Both listed relations 400:

| operator | value | matches |
|---|---|---|
| `is` | `null` | 400 code 103 |
| `is` | `"fin"` | 400 code 103 |
| `is_not` | `null` | 400 code 103 |

Every other route fails too, on its own code:

| call | result |
|---|---|
| `GET ?filter[step_8]=fin` | 400 code 103, `source` `{}` |
| `sort` `step_8` / `-step_8` / `step_0`, `_search` or `GET` | 400 code 104 |
| `_summarize` `grouping` on `step_8` | 500 |
| `_summarize` `summary_fields` `{"field": "step_8", "type": "count"}` | 500 |
| every row above re-run on `Version.step_0` | the same code, the field name and entity type substituted |

**Traps**
- These pass every generic test an inspector applies (`visible: true`, `ui_value_displayable: true`,
  present in `/schema/<Type>/fields`) and then return null for every row.
- Fill-rate scanning breaks twice: the `is_not None` probe 400s like a `checkbox`, and the
  `_summarize` fallback 500s rather than 400s. A scanner that retries on 5xx retries a permanent
  failure 45 times per site.
- Only the write error names the field. A request that 400s with `Read failed for entity type [Shot]`
  gives no clue which sort key caused it; match on code 104 plus the sort you sent.
- `step_0` exists on types that have no Steps at all, so its presence says nothing about whether the
  type is task-tracked. Read `Step.entity_type` for that.

Exclude `data_type == "pivot_column"` from field pickers and from any payload built by iterating the
schema. For the same information, query `Task` filtered on `entity` and `step`, and aggregate
`sg_status_list` yourself.
