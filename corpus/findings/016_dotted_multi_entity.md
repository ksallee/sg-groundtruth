---
tags: [query, dotted-field, multi-entity, filter, paging, trap, silent]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search]
phase: filter
scope: api
measured: first sample project, Shots
verdict: A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.
---

# 016_dotted_multi_entity

**Q** Do dotted paths through a multi-entity field work, for reads and for filters?

**Endpoint** `GET /entity/shots?fields=code,sg_sequence.Sequence.code,tasks.Task.content,assets.Asset.code ; POST /entity/shots/_search`

**Docs claim** Dotted paths are documented for `?fields` and for filters; the docs say nothing about multi-entity fields behaving differently from single-entity ones.

**Actual**

```
data types: {"sg_sequence": "entity", "tasks": "multi_entity", "assets": "multi_entity"}

=== READ: dotted in ?fields
  attributes returned: ['code', 'sg_sequence.Sequence.code']
  attributes returned: ['code', 'sg_sequence.Sequence.code']
  -> single-entity (sg_sequence) present; multi-entity (tasks, assets) SILENTLY ABSENT

=== FILTER: dotted through multi-entity (baseline 300 shots)
  negative controls — must be 0 if the filter is real:
    tasks.Task.content is ZZZNOPE                      -> 0
    assets.Asset.code is ZZZNOPE                       -> 0
    assets.Asset.sg_asset_type is ZZZNOPE (two hops)   -> 0
  positives:
    tasks.Task.content is Comp                         -> 300
    assets.Asset.sg_asset_type is Character            -> 284
    tasks is {type,id}                                 -> 1

=== page size
  asked 500 -> 300 (all)   asked 150 -> 150   asked 50 -> 50
```

**Teaches**
- **Trap.** The read failure is silent and indistinguishable from "no data": the key is not in `attributes`, the same quiet drop a bogus `?fields` name gets (probe 004). Single-entity paths like `sg_sequence.Sequence.code` come back fine, so the difference is the field's `data_type`, not the syntax.
- The filters are evaluated, not ignored: every negative control returns 0, and two hops (`assets.Asset.sg_asset_type`) resolve. On the probed site the positives return partial counts, 284 of 300.
- Filter through multi-entity freely. To read those values, query the child entity separately (`/entity/tasks` filtered by the parent) rather than asking for them inline.
- Corrects probe 005: `page[size]` is not capped at 100. On the probed site 150 returned 150 rows and 500 returned all 300.
