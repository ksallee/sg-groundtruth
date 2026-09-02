---
tags: [query, dotted-field, multi-entity, filter, paging, trap]
verdict: READS and FILTERS differ. Reading a dotted path through a multi_entity field silently omits the key - HTTP 200, no error (single-entity 'entity' fields read fine). But FILTERING on the same path WORKS, including two hops, verified by negative controls returning 0 while positives return partial counts. So: filter through multi-entity freely; to READ those values you must query the child entity separately. Also corrects probe 005: page[size] is NOT capped at 100 - 150 returns 150 and 500 returns everything.
---

# 016_dotted_multi_entity

**Endpoint** `GET /entity/shots?fields=<dotted> ; POST /entity/shots/_search`

**Docs claim** Dotted paths through multi-entity fields.

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

**Verdict** READS and FILTERS differ. Reading a dotted path through a multi_entity field silently omits the key - HTTP 200, no error (single-entity 'entity' fields read fine). But FILTERING on the same path WORKS, including two hops, verified by negative controls returning 0 while positives return partial counts. So: filter through multi-entity freely; to READ those values you must query the child entity separately. Also corrects probe 005: page[size] is NOT capped at 100 - 150 returns 150 and 500 returns everything.
