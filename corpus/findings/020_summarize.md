---
tags: [query, inspector, fill-rate, schema, cost, list-field]
scope: api
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

=== cardinality cap? 300 shots, all distinct codes
  Shot.code -> 300 groups of 300 shots, 374ms

=== cost against the alternative
  one paged fetch of 100 rows   306ms
  one _summarize per field      ~300ms each, up to 1.5s on an entity field
```

**Teaches**
- The `_summarize` endpoint aggregates rows named at call time; the `summary` data type is a per-row rollup defined in the schema (field_types/summary). Same word, different mechanism.
- `grouping` by a field returns one group per distinct value, with empties under a `''` group, so one call gives both cardinality and the empty count. A fill-rate scan gives neither: it calls `code` and `flagged` both 100% (probe 007), while `grouping` returns one group per row for `code` (an identifier) and exactly one group for `flagged` (no information). There is no cardinality cap: on the probed site 300 distinct Shot codes return 300 groups.
- At ~300ms a call, and up to 1.5s on an entity field, scanning every Version field costs many multiples of one paged fetch of 100 rows (306ms on the probed site). Fetch one page for the broad fill-rate pass, then `_summarize` only the shortlist to rank it by cardinality.
- A checkbox cannot be filtered `is_not None`: 400 `API summarize() Version.flagged expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil`. Take fill rate on a checkbox from `grouping`, not from a filter.
- `application/json` is 415 `Unsupported Content-Type 'application/json'`; send the same vendor Content-Type as `_search` (probe 004).
