---
tags: [field-type, calculated, filter, operator, schema, inspector, trap]
scope: api
verdict: A calculated field refuses every write with "is read only" and every filter with "cannot be used in a filter", yet it sorts and summarizes fine, and the formula is exposed as calculated_function.
---

# calculated

**Data type** `calculated`, probed on `Task.workload` (stock, `editable: false`). Four exist on this site:

| entity | field | `calculated_function` | `renderer` | reads back as |
|---|---|---|---|---|
| Task | `workload` | `{duration}` | `duration` | `3000` (int, minutes) |
| Task | `workload_per_day` | `to_days({workload})/ceiling(to_days({duration}))` | `float` | `"0.972222"` (str) |
| Task | `workload_per_day_per_assignee` | `{workload_per_day}/{workload_assignee_count}` | `float` | `"1.0"` (str), null on 21 of 40 rows |
| Asset | `sg_calculated` | `CONCAT({code}, {id})` | `text` | `"charA1,226"` (str) |

Version, Shot, Project, Sequence, Note, PublishedFile and Playlist have none; their computed columns are
`summary` and `pivot_column`, probed separately. None is editable on this site, and `POST /schema/<Type>/fields`
answers the type with a 500 (probe 019): one exists because the web UI made it, or not at all.

| operation | outcome |
|---|---|
| read | plain value in `attributes` |
| create or update | 400 code 103 `API update() Task.workload is read only.` |
| clear | 400, same string |
| filter, any relation | 400 `API read() Task.workload's 'calculated' data type cannot be used in a filter.` |
| sort, `_search` and `GET` | 200, on the computed value |
| `_summarize`, sum and grouping | 200 |

`GET /schema/Task/fields/workload` returns exactly four `properties`:

| property | value on `Task.workload` | `editable` |
|---|---|---|
| `calculated_function` | `{duration}` | true |
| `renderer` | `duration` | true |
| `summary_default` | `sum` | true |
| `default_value` | `null` | false |
| the field's own `editable` | `false` | false |

A client can show the expression and name the fields it reads. The result data type is never stated: `renderer`
is the only declaration, and its values are not `data_type` values.

The value is read-only, the definition is not. `PUT /schema/Task/fields/workload` with
`{"properties": [{"property_name": "calculated_function", "value": "{duration}"}]}` returns 200 and the full field
record. The formula is site-wide, so rewriting it changes every row of that type on every project at once; there
is no project-scoped calculated field.

**Read** A plain value in `attributes`, never `relationships` (`relationships` is `{}` on a Task), returned when
named in `fields` and in `fields=*` (37 of 56 Task attributes). The shape follows `renderer`, not the operands:

| `renderer` | JSON shape | example |
|---|---|---|
| `duration` | int, minutes | `workload` 3000, matching `duration` 3000 |
| `float` | string, 6 decimals | `"0.972222"`, `"1.0"`, `"0.625"` |
| `text` | string, numbers formatted | `"charA1,226"` for id 1226 |

`PUT {"duration": 480}` then reading the row back returns `workload: 480` on the next request, through both
`GET /entity/tasks/<id>` and `_search`; `duration: null` returns `workload: null`.

**Write** Every form tried on `Task.workload`, on a throwaway sandbox Task:

| sent | result |
|---|---|
| `POST /entity/tasks {"workload": 480}` | 400 `API create() Task.workload is read only.` |
| `PUT {"workload": 480}` | 400 `API update() Task.workload is read only.` |
| `PUT {"workload": "480"}` | 400, same string |
| `PUT {"workload": "{duration}*2"}` | 400, same string |

Every refusal returns code 103 and an empty `source`, and the row reads back unchanged. Match on `status` and
`code: 103`, not on `source`, which a type error fills with the field name. Nothing is accepted and discarded,
unlike `cached_display_name`: `editable: true`, a 200, value dropped (probe 004).

**Clear**

| sent | result |
|---|---|
| `null` | 400 `API update() Task.workload is read only.` |
| `""` | 400, same string |
| `0` | 400, same string |

The value stays whatever the formula computes. To empty one, write null to the field its formula reads:
`{"duration": null}` gives `workload: null`, changing the operand too.

**Filter** No relation is accepted, and none is enumerated the way probe 017's types are:

```
["workload", "definitely_not_an_operator", null] -> 400
 title:  "API read() Task.workload's 'calculated' data type cannot be used in a filter."
 source: {"Task.workload": " data type cannot be used in a filter. Value: {"path" => "workload",
          "relation" => "definitely_not_an_operator", "values" => [nil]}"}
```

| filter | result |
|---|---|
| `is` null, `is_not` null | 400, same string |
| `is` 0, `is` 480 | 400, same string |
| `greater_than` 0, `less_than` 100000 | 400, same string |
| `in` [480] | 400, same string |
| any of the above on `workload_per_day` or `Asset.sg_calculated` | 400, same string |

Sorting and summarizing work, on the computed value:

| call | result |
|---|---|
| `_search {"sort": "workload"}` | 200, first 5 `[0,0,0,0,0]` |
| `_search {"sort": "-workload"}` | 200, `[6000 x5]` |
| `GET ?sort=-workload` | 200, `[6000, 6000, 6000, 6000, 6000]` |
| `_summarize` sum(workload) | 200 `{"summaries": {"workload": 5676600}}` |
| `_summarize` grouping exact | 200, `group_name` `"1.25 days"`, `group_value` `"600.000000"`, 11 groups |

**Traps**
- **Filter it by rewriting the formula.** `["workload", "is", 600]` 400s; `["duration", "is", 600]` gets the
  same rows for `{duration}`. There is no equivalent for `CONCAT({code}, {id})`: page and match client-side.
- Sort is the one query verb that survives. Top-N by a computed column is one call; rows where that
  column is over X is a full scan.
- A `float` renderer returns a string, so `sorted(rows, key=...)` on the raw value sorts
  lexicographically and puts `"0.9"` after `"0.625"`. Cast before comparing (field_types/float).
- A `text` renderer formats numeric operands for display: `CONCAT({code}, {id})` on id 1226 gives
  `"charA1,226"`, a thousands separator inside a string a client might parse back.
- Division by null yields null, not an error: `workload_per_day_per_assignee` is null on 21 of 40 rows where
  `{workload_assignee_count}` is 0. Fill rate measures the operands, so drop the type from fill ranking as
  probe 007 drops checkbox and summary.
- `default_value` is present in `properties` and always null. Nothing sets it; do not read it as the
  value of an unpopulated row.
