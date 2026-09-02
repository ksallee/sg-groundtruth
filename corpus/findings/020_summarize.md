---
tags: [query, inspector, fill-rate, schema, cost, list-field]
verdict: _summarize takes the SAME vendor Content-Type as _search (application/json is 415, probe 004) and answers the inspector's second question directly: `grouping` by a field returns one group per distinct value with a count, so ONE call yields both cardinality and the empty count - empty values come back as a '' group. That is the metric fill rate cannot give: Version.code returns one group per row (an identifier, useless to expose) and flagged returns exactly one group (no information at all), while both look identical to a fill-rate scan. Grouping is NOT capped - 300 distinct Shot codes return 300 groups. Checkbox fields cannot be filtered `is_not None` at all (400), which is the same trap as probe 007 from the other side. BUT it is not free: ~300ms typical and up to 1.5s when the grouped field is an entity, so scanning all 61 Version fields costs far more than a single paged fetch of 100 rows. Use one fetch for the broad fill-rate pass, then _summarize per candidate field to rank the shortlist by cardinality.
---

# 020_summarize

**Endpoint** `POST /entity/<type>/_summarize`

**Docs claim** Summarize is a cheap aggregate call.

**Actual**

```
=== content type: same vendor requirement as _search (probe 004)
  vendor array Content-Type -> 200 {"summaries": {"id": 100}, "groups": []}
  application/json          -> 415 Unsupported Content-Type 'application/json'

=== grouping: one group per distinct value, and '' for empty
  field              groups     ms  interpretation
  sg_status_list          5   1650  5 values, 0 empty
  entity                 51   1541  51 values, 0 empty
  code                  100    319  identifier - every row distinct
  sg_task                 2    283  2 values, 99 empty
  flagged                 1    370  no information - one value
  description             4    306  4 values, 0 empty
  sg_version_type         2    305  2 values, 1 empty

=== fill rate without fetching rows
  sg_task            200 1/100
  image              200 1/100
  description        200 100/100
  sg_path_to_movie   200 0/100
  flagged            400 API summarize() Version.flagged expected [String, FalseClass, TrueClas/100

=== summary types
  frame_count count    -> 200 {"summaries": {"frame_count": 0}, "groups": []}
  frame_count sum      -> 200 {"summaries": {"frame_count": 0}, "groups": []}
  frame_count average  -> 200 {"summaries": {"frame_count": 0.0}, "groups": []}
  frame_count maximum  -> 200 {"summaries": {"frame_count": 0}, "groups": []}
  frame_count minimum  -> 200 {"summaries": {"frame_count": 0}, "groups": []}

=== cardinality cap? 300 shots, all distinct codes
  Shot.code -> 300 groups of 300 shots, 398ms

=== cost against the alternative
  one paged fetch of 100 rows          706ms
  ~300ms x 61 fields of _summarize     ~18300ms
```

**Verdict** _summarize takes the SAME vendor Content-Type as _search (application/json is 415, probe 004) and answers the inspector's second question directly: `grouping` by a field returns one group per distinct value with a count, so ONE call yields both cardinality and the empty count - empty values come back as a '' group. That is the metric fill rate cannot give: Version.code returns one group per row (an identifier, useless to expose) and flagged returns exactly one group (no information at all), while both look identical to a fill-rate scan. Grouping is NOT capped - 300 distinct Shot codes return 300 groups. Checkbox fields cannot be filtered `is_not None` at all (400), which is the same trap as probe 007 from the other side. BUT it is not free: ~300ms typical and up to 1.5s when the grouped field is an entity, so scanning all 61 Version fields costs far more than a single paged fetch of 100 rows. Use one fetch for the broad fill-rate pass, then _summarize per candidate field to rank the shortlist by cardinality.
