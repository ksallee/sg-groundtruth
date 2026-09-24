---
tags: [query, summary, cost, page]
endpoints: [POST /entity/<type>/_summarize, GET /schema/<Type>/fields/<field>]
phase: filter
scope: api
measured: sample project 1 of 1, 300 Shots, Shot.open_notes_count
coverage: partial
unmeasured: A Note linked to two Shots: the probed project has none, so crediting one group to several parents is untested. single_record fields have no grouped form. Blocked on the site.
verdict: One _summarize with the parent leaf as `in [N rows]`, grouped on that link, reproduced open_notes_count for 300 Shots in 573 ms, against ~290 ms a row one call at a time.
---

# 080_query_field_cost

**Q** Can one `_summarize` grouped on the link reproduce a query field's value for N rows at once, and what do N per-row calls cost?

**Endpoint** `GET /schema/Shot/fields/open_notes_count ; POST /entity/notes/_summarize`

**Docs claim** Silent.

**Actual**

```
Shot.open_notes_count: record_count of Note.id
  query {"logical_operator": "and", "conditions": [
    {"path": "note_links", "relation": "is", "values": [{"id": 0, "name": "Current Entity", "type": "Entity", "valid": "parent_entity_token"}]},
    {"logical_operator": "or", "conditions": [sg_status_list is opn, is ip, is rdy]}]}

per row, the first 50 Shots: 50 calls, 14449 ms, median 287 ms, max 328 ms; equals the stored field on 50 of 50

grouped: [note_links, "in", [N Shots]] plus the rest of the tree, grouping [{"field": "note_links", "type": "exact"}]
  N=50   one call 339 ms, 50 groups, agrees with per-row on 50 of 50
  N=300  one call 573 ms, 300 groups, agrees with the stored field on 300 of 300
  group_value on a multi_entity grouping: a list, [{"type": "Shot", "id": <id>, "name": "sh010", "valid": "valid"}]
notes in the project 5944; linked to more than one Shot 0
```

**Teaches**

- Rewrite the `parent_entity_token` leaf from `is <row>` to `in [<every row on screen>]`, keep the rest of
  the query, and group on the same path. Each group is one parent's value; a parent with no group is 0
  for `record_count`.
- On the probed site that is 573 ms for 300 Shots against ~87 s for 300 per-row calls, and the cost grew
  from 339 ms to 573 ms between 50 and 300 rows.
- **A multi_entity grouping keys on the whole link list.** `group_value` is a list, and a Note linked to a
  Shot and a Version lands in a group naming both. Credit a group's value to every parent it names.
  On the probed site no Note links two Shots, so double-counting under that rule was not observable.
- This covers the aggregating flavours (`record_count`, `sum`, `count`, ...), which group. A
  `single_record` field (a sorted row 0, recipe 003) has no grouped form: it stays one `_search` per row.
