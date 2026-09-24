---
tags: [page, filter, operator, query, trap]
endpoints: [POST /entity/<type>/_summarize, GET /schema, GET /schema/<Type>/fields]
phase: filter
scope: api
measured: site-wide, 3426 stored filter trees; project tokens filled from sample project 1 of 1 where a page has none
coverage: partial
unmeasured: in_calendar_* relations, multi-hop paths and summary-field paths: no stored tree on the probed site uses one. 306 trees whose parent type has no row here. Blocked on the site.
verdict: Every stored page filter with its tokens filled converts and runs 200 but one, yet recipe 003 kept unticked leaves (active "false"): 11 trees returned the wrong count. Drop them.
---

# 074_page_filter_coverage

**Q** Does recipe 003's `convert()` translate every filter tree stored on a page, and does the server accept what it produces?

**Endpoint** `POST /entity/<type>/_summarize` (record_count, api3_hash), one per distinct (type, filters)

**Docs claim** Silent. The stored tree is the web interface's format.

**Actual**

```
3468 query widgets; filters absent or null on 42, a tree on 3426
leaves by (relation, values): is/1 6112, is_not/1 135, in_last/2 9, contains/1 1; in_calendar_*: 0
leaves by path shape: plain 5554, plain on a type the schema no longer has 430, one hop 268,
  one hop through a pivot column (step_0.Task.sg_status_list) 5; two hops or more 0; a summary field 0
entity values by `valid`: valid 3142, parent_entity_token 2722, autocomplete 34, project_token 21,
  absent 19, logged_in_user_token 5
parent_entity_token stored `type`: Entity 1693, Asset 232, Sequence 172, Scene 172, Task 129, ..., "None" 4

recipe 003 convert(), tokens filled (project from Page.project, parent a live row, user FPT_USER_LOGIN):
  trees on a type absent from GET /schema, not sent: 187 over 8 types (disabled since the page was made)
  200 2932 | convert raised 306 | 400 1        distinct (type, filters) sent: 1536
  306x KeyError: "no substitution for token 'parent_entity_token'"   (no row of the parent's type on this site)
    1x 400 "API summarize() Contract.project doesn't exist."   a project filter on a type with no project field
autocomplete, 34 leaves on 17 trees: {"name": "<typed text>", "valid": "autocomplete", "project_ids": [<id>]}

unticked leaves: `active` "true" 5527, true 501, "false" 225, absent 4
  182 trees hold one; counted with it and without it: same 171, different 11, e.g.
  Asset   with 0   without 4     unticked {"path": "project", "relation": "is", "values": [null],
  Version with 0   without 6               "top_level_project_filter": true, "active": "false"}
  Asset   with 0   without 139
empty root group {"logical_operator": "and", "conditions": []} on Shot -> 200, every Shot
```

**Teaches**

| stored | converts | action |
|---|---|---|
| `is`, `is_not`, `contains` with one value | yes | `[path, relation, values[0]]` |
| `in_last` with `[n, unit]` | yes | `LIST_RELATIONS` keeps the list |
| a one-hop path, a `step_N` pivot path | yes | send as stored |
| `active: "false"` on a leaf | yes, and wrongly | drop the leaf: the web interface does not apply an unticked condition |
| `parent_entity_token` | yes, given the row | its stored `type` is a label (`Entity`, the string `"None"`); send the row's real type |
| `autocomplete` | no | typed text with no id; refuse the page |
| a project filter on a type with no `project` | 400 `<Type>.project doesn't exist.` | drop `top_level_project_filter` leaves on such a type |
| a widget whose `entity_type` is no longer in `GET /schema` | not sent | check the type first; the 400 is about the type, not the filter |

- **The only silent failure is the unticked leaf.** On a site-level page the project condition is stored
  unticked with a null value; kept, it narrows to `project is null` and returns 0 rows at 200. Recipe 003
  now drops unticked leaves.
- On the probed site no stored tree uses `in_calendar_*`, a two-hop path or a summary-field path, so the
  corpus has no evidence for them. Probe 017 enumerates the relations; run one before trusting it.
- `valid` absent on 19 values means a real row, as `"valid"` does: keep `{type, id}`.
