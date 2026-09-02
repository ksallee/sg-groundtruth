---
tags: [query, filter, operator, header, page, error-handling, trap]
scope: api
verdict: api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.
---

# 030_complex_filters

**Q** How are boolean and nested filters expressed, and what are their limits?

**Endpoint** `POST /entity/<type>/_search ; POST /entity/<type>/_summarize ; GET /entity/<type>`

**Docs claim** Filters are `[field, operator, value]`. Nothing about `or`, nesting, or combining a
query-string `filter[]` with a body filter.

**Actual**

```
baseline 500 shots (the page cap, so 500 means no filter applied); rows 862 and 863 are disjoint on id
api3_hash, the whole filters value
  {"logical_operator":"or","conditions":[["id","is",862],["id","is",863]]} -> 2 ids [862,863]
  the same conditions under "and" -> 0         "conditions": [] -> 500, every row
  "AND" "OR" "Or" "not" "xor" "nand" "" -> 400 "Invalid logical operator: AND"
  {"conditions":[...]}      -> 400 "Missing logical operator: {"conditions" => [["id", "is", 862], ...]}"
  {"logical_operator":"or"} -> 400 "Missing conditions parameter: {"logical_operator" => "or"}"
depth: N and-groups wrapping an or-leaf (must stay 2) and an and-leaf (must stay 0)
  1 2 3 5 10 20 50 100 200 250 265 -> 2 / 0 at every depth
  266 300 500 1000 5000            -> 500 {"title": "Shotgun Server Error", "source": null}
  265 -> [2,2,2] and 266 -> [500,500,500] over three runs
  size is not the limit: one or-group of 5000 sibling conditions, 90090 bytes -> 2
api3_array
  [["id","is",862],["id","is",863]]   -> 0   the flat list is an implicit and
  [[["id","is",862],["id","is",863]]] -> 400 "Invalid condition: [["id", "is", 862], ["id", "is", 863]]"
  [["id","is",862,"or"]]              -> 400 "Invalid condition: ["id", "is", 862, "or"]"
  [{"logical_operator":"or","conditions":[...]}] and ["or",["id","is",862],["id","is",863]]
    -> 400 "Invalid filter. Expected array of basic condition arrays but received: [...]"
  {"logical_operator":"or","conditions":[...]} -> 400 "Query is not an Array: {...}"
query string on POST _search: the param is not read, the body decides
  ?filter[id]=863                  + body ["id","is",862]       -> 1 ids [862]
  ?filter[project.Project.id]=<p1> + body ["id","is",1174]      -> 1 ids [1174], 1174 is in <p2>
  ?filter[id]=1174                 + body ["project","is",<p1>] -> 300
  ?filter[zzz_not_a_field]=1       + body ["id","is",862]       -> 1 ids [862]
  GET /entity/shots?filter[id]=863                              -> 1 ids [863]
{"path":"id","relation":"is","values":[862]}, one page-storage leaf (probe 023)
  api3_hash, as a condition and as the whole filters value, _search and _summarize
    -> 400 "Missing logical operator: {"path" => "id", "relation" => "is", "values" => [862]}"
  api3_array [obj], _search and _summarize
    -> 400 "Invalid filter. Expected array of basic condition arrays but received: [...]"
```

**Teaches**

**Boolean logic needs `api3_hash`.** The two vendor Content-Types are not interchangeable, and a client
that wants anything but a conjunction needs both, or `api3_hash` throughout. `api3_hash` also expresses
a plain `and`, so one Content-Type covers every case.

| Content-Type | `filters` accepted | boolean logic |
|---|---|---|
| `api3_array` | `[[field, op, value]]`, and only that | `and` of the list, implicit; no other spelling |
| `api3_hash` | `{"logical_operator", "conditions"}`, conditions being triples or further groups | `and` and `or`, nested |

Four spellings of a boolean under `api3_array` all 400: a nested list, a group object inside the list,
an operator string as the first element, and a fourth element on a triple. `["id","is",862,"or"]` is
`400 Invalid condition`, so the shape is fixed at three elements.

- **Top-level `or` works.** It is the whole `filters` value, not something that has to sit inside an
  `and`. `or` over two conditions disjoint on `id` returns both rows and `and` over the same two returns
  0, so the operator is applied rather than defaulted.
- `and` and `or` are the whole vocabulary, lowercase. `AND`, `OR`, `Or`, `not`, `xor`, `nand` and `""`
  are each `400 Invalid logical operator: <what you sent>`. There is no negation operator; use the
  negative relations (`is_not`, `not_contains`, `not_in`) from probe 017 on the leaf.
- Both keys are required and neither is inferred: a group without `logical_operator` is
  `400 Missing logical operator`, one without `conditions` is `400 Missing conditions parameter`.
  `"conditions": []` is 200 and matches every row, so an empty group is not a no-match, it is no filter.
- **Depth stops at 265 groups, loudly.** 266 is `500 {"title": "Shotgun Server Error", "source": null}`,
  repeatably, with no `source` to read. Nothing is silently truncated below that: the control, an
  `and` of two disjoint conditions at the innermost level, returns 0 at every depth from 1 to 265,
  where a dropped inner group would return the full page. The limit is depth, not payload: one flat
  `or` group of 5000 conditions at 90090 bytes is 200.
- **A query-string `filter[]` on `POST _search` is read by nothing.** `?filter[id]=863` alongside a body
  filter selecting row 862 returns row 862; `?filter[project.Project.id]=<p1>` alongside a body filter
  selecting a row in another project returns that other row. A misspelled `?filter[zzz_not_a_field]=1`
  is 200, where the same name in a body filter is 400 (probe 004). The same parameter on the `GET`
  listing endpoint filters correctly, so the two endpoints take their filters in different places and
  a client moving from `GET` to `_search` must move the filter into the body.
- **The `{path, relation, values}` object runs nowhere over REST.** It is rejected as a condition inside
  a group, as the whole `filters` value, under both Content-Types, and on `_summarize` as well as
  `_search`. It is the web interface's storage format only (probe 023) and the rollup definition format
  (`field_types/summary`), so converting a saved page's filters into a query is a translation, never a
  pass-through: rewrite each leaf `{"path": p, "relation": r, "values": v}` as a triple and keep the
  `logical_operator` groups as they stand. The group's own extra keys are tolerated: `filter_name`,
  `filter_id` and an unknown key alongside triple conditions are all 200. The leaf's are not, so drop
  them rather than appending; `active` and `top_level_project_filter` both appear (`recipes/003`).
  `v[0]` is right only where the relation takes a scalar. `in_last` and `in_next` take the whole list,
  and passing the first element alone is 400 `expects a 2-element array: [4]` (`recipes/003`), so the
  translator branches on the relation rather than flattening every leaf the same way.
- One group holds mixed operators and mixes leaf conditions with sub-groups as siblings, which is what
  the stored page trees do. `and [["project","is",<p1>], {"or": [id is 862, id is 863]}]` returns 2 and
  the same with an inner `and` returns 0. Dotted paths work inside a nested group, and an error inside
  one is reported as at the top level: a bogus operator 400s with the field's `Valid relations` list,
  a bogus field with `API read() Shot.sg_not_a_field doesn't exist.`

**Python equivalent** `shotgun_api3` spells the same tree with different keys: `filter_operator` for
`logical_operator`, `filters` for `conditions`, `all` for `and` and `any` for `or`.

```python
sg.find("Shot", [{"filter_operator": "any",
                  "filters": [["id", "is", 862], ["id", "is", 863]]}])
```
