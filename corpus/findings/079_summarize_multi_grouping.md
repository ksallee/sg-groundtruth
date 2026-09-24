---
tags: [summary, status, query, page]
endpoints: [POST /entity/<type>/_summarize]
phase: filter
scope: api
measured: sample project 1 of 1, 300 Shots, 1900 Tasks, 100 Versions
verdict: _summarize nests one group level per grouping entry, 3 deep tested, counts summing exactly. status_list rolls a group up to one status; status_percentage ignores any value and is no per-status share.
---

# 079_summarize_multi_grouping

**Q** Does `_summarize` nest two `grouping` entries, and what do `status_percentage` and `status_list` return on `sg_status_list`?

**Endpoint** `POST /entity/<type>/_summarize`

**Docs claim** Grouping takes a list. Silent on nesting and on what the status types compute.

**Actual**

```
Shots grouped [sg_sequence, sg_status_list] -> 200, 15 groups, total {"id": 300}
  {"group_name": "seq01", "group_value": {"type": "Sequence", "id": <id>, "name": "seq01", "valid": "valid"},
   "summaries": {"id": 20}, "groups": [{"group_name": "wtg", "group_value": "wtg", "summaries": {"id": 3}},
                                        {"group_name": "ip", "group_value": "ip", "summaries": {"id": 8}}, ...]}
  each parent's count equals the sum of its children: True
Tasks grouped [entity, step, sg_status_list] -> 200, nesting depth 3
Tasks grouped on entity.Shot.sg_sequence -> 200, 16 groups; on start_date by week -> 200, 19 groups
bogus grouping type -> 400 "type must be one of: exact, tens, hundreds, thousands, tensofthousands,
  hundredsofthousands, millions, day, week, month, quarter, year, clustered_date, oneday, fivedays,
  entitytype, firstletter"

status_percentage over the project, then per status group (value, rows, status_percentage):
  shots     0 over 300    [(wtg, 183, 0), (ip, 64, 0), (fin, 53, 0)]
  tasks     3 over 1900   [(wtg, 851, 0), (ip, 139, 0), (fin, 844, 0), (apr, 4, 0), (null, 62, 0)]
  versions  0 over 100    [(na, 28, -1), (rev, 29, 0), (vwd, 21, 0), (apr, 20, 0), (fin, 2, 0)]
  status_percentage_as_float: 0, 3, 0, the same integers
  shots with "value": "fin", "values": ["fin"] or "status": "fin" -> 200 {"sg_status_list": 0}
status_list per group, against the statuses in it:
  [wtg] -> wtg   [fin] -> fin   [ip, wtg] -> ip   [fin, ip] -> ip   [fin, ip, wtg] -> ip
  [null, fin, wtg] -> ip   ... 12 distinct pairs over the Tasks, every mixed set -> ip
```

**Teaches**

- **Nested groups are one call.** Each `grouping` entry adds a level: a group holds `groups` with the
  next field's groups, and the leaf level has no `groups` key. Group headers for a page grouped two or
  three deep cost one `_summarize`, not a page of rows. Grouping takes a dotted path and the date buckets
  the web interface stores (`week`, probe 073).
- **`status_list` is the roll-up.** One status alone rolls up to itself; any mix rolls up to `ip`, even
  `[null, fin, wtg]` where no row is `ip`. On the probed site that is the rule on every group measured.
  It honours a field's excluded statuses (probe 091).
- **`status_percentage` does not answer "what share is `fin`".** It ignores `value` and every other key
  sent, returns an integer under both names, and gave 3 on Tasks where 62 of 1900 rows (3.3%) have no
  status and -1 on a group of `na` Versions. Compute a status share yourself from one grouped count:
  `rows in status / rows in group`.
- The page grid summary `{"type": "status_percentage", "value": "fin"}` (probe 073) is therefore not a
  `_summarize` call; reproduce it from the `grouping` on `sg_status_list`.
