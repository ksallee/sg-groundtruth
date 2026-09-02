---
tags: [query, inspector, fill-rate, schema, cost, list-field]
scope: api
measured: 3 sample projects, Versions
verdict: _summarize needs the same vendor Content-Type as _search, and one `grouping` call returns a field's distinct-value count and its empty count. At ~300ms a field, rank a shortlist, never scan.
---

# 020_summarize

**Q** Can `_summarize` answer the inspector's per-field questions more cheaply than fetching rows?

**Endpoint** `POST /entity/<type>/_summarize`

**Docs claim** Summarize is a cheap aggregate call.

**Actual**

```
=== content type: same vendor requirement as _search (probe 004)
  vendor array Content-Type -> 200 {"summaries": {"id": 100}, "groups": []}
  application/json          -> 415 Unsupported Content-Type 'application/json'

=== grouping: one group per distinct value, and '' for empty
  field              groups     ms  interpretation
  sg_status_list          5    299  5 values, 0 empty
  entity                 51    315  51 values, 0 empty
  code                  100    301  identifier - every row distinct
  sg_task                 2    310  2 values, 99 empty
  flagged                 1    378  no information - one value
  sg_version_type         2    667  2 values, 1 empty

=== fill rate without fetching rows
  sg_task            200 1/100
  description        200 100/100
  sg_path_to_movie   200 0/100
  flagged            400 API summarize() Version.flagged expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil

=== summary types
  frame_count count/sum/maximum/minimum -> 200 {"summaries": {"frame_count": 0}, "groups": []}
  frame_count average                   -> 200 {"summaries": {"frame_count": 0.0}, "groups": []}

=== cardinality cap? no cap found below 1009 groups
  Shot.code, one project    -> 300 groups of 300 shots, 374ms
  Version.code, whole site  -> 1009 groups of 1057 versions, 425ms

=== cost against the alternative
  one paged fetch of 100 rows   306ms
  one _summarize per field      ~300ms each, up to 1.5s on an entity field
```

**Teaches**
- The `_summarize` endpoint aggregates rows named at call time; the `summary` data type is a per-row rollup defined in the schema (field_types/summary). Same word, different mechanism.
- `grouping` by a field returns one group per distinct value, with empties under a `''` group, so one call gives both cardinality and the empty count. A fill-rate scan gives neither: it calls `code` and `flagged` both 100% (probe 007), while `grouping` returns one group per row for `code` (an identifier) and exactly one group for `flagged` (no information). No cap showed below 1009 groups: on the probed site an unfiltered `Version.code` grouping returns 1009 groups over 1057 rows in 425ms, and one project's 300 distinct Shot codes return 300 groups.
- At ~300ms a call, and up to 1.5s on an entity field, scanning every Version field costs many multiples of one paged fetch of 100 rows (306ms on the probed site). Fetch one page for the broad fill-rate pass, then `_summarize` only the shortlist to rank it by cardinality.
- A checkbox cannot be filtered `is_not None`: 400 `API summarize() Version.flagged expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil`. Take fill rate on a checkbox from `grouping`, not from a filter.
- `application/json` is 415 `Unsupported Content-Type 'application/json'`; send the same vendor Content-Type as `_search` (probe 004).
- A bogus `type` 400s `Request Parameters invalid.` and `source.summary_fields` names the whole set, indexed by position in the list: `type must be one of: record_count, count, sum, maximum, minimum, average, earliest, latest, percentage, status_percentage, status_percentage_as_float, status_list, checked, unchecked`. Ask the endpoint rather than guessing (probe 017).

**One summary type per field per call.** `summaries` is an object keyed by field name, so a second entry
for the same field overwrites the first at 200, with nothing in the response to say so. The last entry wins.
On the probed site, over 100 versions:

| `summary_fields` | `summaries` |
|---|---|
| `id count` | `{"id": 100}` |
| `id maximum` | `{"id": 25568}` |
| `id count` + `id maximum` | `{"id": 25568}` |
| `id maximum` + `id count` | `{"id": 100}` |
| `id count` + `id count` | `{"id": 100}` |
| `id count` + `id minimum` + `id maximum` | `{"id": 25568}` |
| `id count` + `frame_count sum` | `{"id": 100, "frame_count": 0}` |

Two types over one field costs two calls. Two different fields in one call return both.

**A group's label and its value are not interchangeable.** `group_value` is what the grouping was
computed on; `group_name` is the server's render of it for display:

| grouping field | `group_name` | `group_value` |
|---|---|---|
| `user`, an entity field | `"<user>"` | `{"type": "HumanUser", "id": 385, "name": "<user>", "valid": "valid"}` |
| `sg_task`, an entity field, no value set | `""` | `null` |
| `sg_status_list`, a list field | `"na"` | `"na"` |
| `workload`, a calculated field | `"1.25 days"` | `"600.000000"` (field_types/calculated) |

Key on `group_value`, display `group_name`. On an entity grouping `group_value` is the full reference
object, so `group_value.id` identifies the group and survives a rename; `group_name` is the display name
and is not unique. On the probed site a `user` grouping over 100 versions returned 7 groups under 6
distinct `group_name`, two HumanUsers of different id sharing one display name. A client keyed on
`group_name` merges those two people into one row.
