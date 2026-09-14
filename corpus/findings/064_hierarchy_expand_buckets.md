---
tags: [path, project, sequence, trap]
endpoints: [POST /hierarchy/_expand, POST /hierarchy/_search]
phase: read
scope: api
measured: sample project 1 of 1, plus the Shot node of every project on the site, read only
coverage: partial
unmeasured: how the web interface draws the repeated node. Its tree needs a session a person approves (probe 052), and the saved token had expired
verdict: Dedupe `children` by `path` and keep the first. The `__none__` bucket is repeated once per group, byte-identical every time, and its rows are disjoint from every group's.
---

# 064_hierarchy_expand_buckets

**Q** Why does expanding a project's Shot node answer the same "no group" node once after every
sequence, and what is behind that path?

**Endpoint** `POST /hierarchy/_expand ; POST /hierarchy/_search`

**Docs claim** The reference gives `children` as the next level of the tree. Nothing in it says a
child can repeat, so a client indexing `children` by `path` or drawing one row per entry gets a
different tree from the one the site means.

**Actual**

```
=== /Project/70/Shot   15 Sequence rows, 300 Shots, 0 of them unsequenced
30 children, order gBgBgBgBgBgBgBgBgBgBgBgBgBgBgB      g a Sequence, B the bucket
  g {"label": "seq01", "path": "/Project/70/Shot/sg_sequence/Sequence/23",
     "ref": {"kind": "entity", "value": {"type": "Sequence", "id": 23}}, "has_children": true}
  B {"label": "Shots with no Sequence", "path": "/Project/70/Shot/sg_sequence/Sequence/__none__",
     "ref": {"kind": "entity_type", "value": "Shot"}, "has_children": true}
every B serialises identically, key order included; a second call and one sending
seed_entity_field are byte-identical

=== the bucket path, expanded
/Project/70/Shot/sg_sequence/Sequence/__none__ -> 200, byte-identical across two calls
  children [{"label": "No Shots", "ref": {"kind": "empty", "value": null}, "has_children": false}]
another project, 6 sequences and 5 unsequenced Shots -> 200, 5 children, kind entity
  27 rows under the 6 groups, 0 of them also in the bucket, 32 distinct against 32 Shots

=== every project on the site: the bucket count follows the groups, not the ungrouped rows
project  sequences  groups  buckets  shots  unsequenced  order
70       15         15      15       300    0            gBgB... (15 pairs)
91       6          6       6        32     5            gBgBgBgBgBgB
396      44         44      44       44     44           gBgB... (44 pairs, every group empty)
1180     0          1       0        13     13           g
1180 -> [{"label": "No Shots", "ref": {"kind": "empty", "value": null}, "has_children": false}]
  /Project/1180/Shot/sg_sequence/Sequence/__none__ -> 200, 13 children, kind entity

=== /Project/70/Asset, grouped by a list field: 13 children, ggggggggggggB, every kind list
  B {"label": "Assets with no Type", "path": "/Project/70/Asset/sg_asset_type/__none__",
     "ref": {"kind": "list", "value": "__none__"}}

=== POST /hierarchy/_search spells the bucket without the type segment; both answer the 5 rows
  "/Project/91/Shot/sg_sequence/__none__"  -> 200 "Shots with no __none__"
```

**Teaches**

- **Dedupe `children` by `path` and keep the first.** The bucket is emitted once after every group
  and each copy serialises identically, key order included, so the first is the whole of it.
- The repeat count is the number of groups, not the number of ungrouped rows. On the probed site one
  project has 44 empty sequences and 44 unsequenced Shots: 44 groups that expand to `No Shots`, and
  44 copies of the one bucket that holds all 44 rows.
- `has_children: true` on the bucket is a shape, not a count. A project with nothing ungrouped still
  lists it, and expanding it answers a single child of `"kind": "empty"` labelled `No Shots`.
- A row is under the bucket or under a group, never both. Bucket rows and group rows summed to the
  project's own Shot count on both projects measured that way.
- **A grouping field with no rows hides every row under it.** On the probed site a project with 13
  Shots and no Sequence answers `/Project/<id>/Shot` as one `"kind": "empty"` child labelled
  `No Shots`, with no bucket among the children. The bucket path answers all 13 when asked for
  directly, so build it rather than trusting `children` to name it.
- Grouping by a list field repeats nothing: `/Project/<id>/Asset` returns one `__none__` child, last,
  with `"kind": "list"`. The repetition measured here is the entity-grouped case.
- `_expand` and `_search` spell the same bucket differently, and both answer: `_search` writes
  `sg_sequence/__none__` where `_expand` writes `sg_sequence/Sequence/__none__`. The label is
  templated off the segment, so the first reads `Shots with no __none__`.
