---
tags: [task-template, dependency, batch, destructive, trap]
endpoints: [POST /entity/_batch, POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/<type>/_search, GET /entity/<type>/<id>, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2 templates, 2 Shots, 18 Tasks and their edges made and deleted by the probe; 50.9 s, 125 calls
verdict: An undo's write back to template A erases every edge whose downstream Task is A-linked and that A lacks, pre-merge edges included; recipe 022 DELETEs one such edge, 404s and rolls back.
---

# 111_template_undo_outside_edge

**Q** When the undo of a merge writes `task_template` back to the old template A (recipes 019, 022),
which edges does that write erase: a re-created outside edge, a mixed edge, an edge between two
A-linked Tasks that A lacks?

**Endpoint** `POST /entity/_batch ; PUT /entity/shots/<id> ; POST /entity/task_dependencies ; POST /entity/task_dependencies/_search ; GET /entity/task_dependencies/<id> ; DELETE /entity/<type>/<id>`

**Docs claim** Silent. Probe 104 left mixed ends unmeasured; probe 109 measured the apply, not the undo.

**Actual**

A: comp, roto, lay; roto on comp. B: comp, lay, paint; lay on comp start-to-start 1, paint on lay. Twin Shots M, W
made with A, plus unlinked x, y and hand edges comp on x, roto on x, roto on lay. Merge: recipe 020's
batch (comp, lay claimed to B). Then by hand: R1 comp on x (re-created), R2 roto on paint, R3 y on lay.
W undone by recipe 019's calls, edges read after each step; M by recipe 022's batch.

| edge | kind | merge | W step 2, `task_template` A | M, retired read |
|---|---|---|---|---|
| roto on comp | A's own | kept, same id | **re-created, new id** | old id 404 / 404 |
| comp on x | pre-merge, A-linked down, extra up | erased | (already gone) | 404 / 404 |
| roto on x | pre-merge, roto never claimed, extra up | kept | **erased** | 404 / 404 |
| roto on lay | pre-merge, both A-linked, A lacks | kept | **erased** | 404 / 404 |
| lay on comp | B's, both back on A, A lacks | made | erased | (probe 104) |
| R1 comp on x | re-created after merge, down back on A | made by hand | **erased** | 404 / 404 |
| R2 roto on paint | A-linked down, merge-made up | made by hand | erased | 404 / 404 |
| paint on lay | B's, merge-made down, up back on A | made | kept | retired with paint |
| R3 y on lay | extra down, up back on A | made by hand | kept | DELETEd by the batch: 404 / 200 |

```
W step 1 claims back to A -> 200, 200; edges unchanged
W step 2 PUT Shot task_template=A -> 200; edges: paint on lay, roto on comp #4615 (new), y on lay
W step 3 DELETE paint 204, y on lay 204, roto on comp #4615 204 (not in the snapshot's ids) -> no edge
M recipe 022 batch as written, edge DELETEs [comp on x #4607, y on lay #4609]
  -> 404 "Entity of type [TaskDependency] with id=4607 does not exist."  edge ids unchanged
M same batch, edges whose downstream end goes back to an A task left out: DELETE [y on lay] -> 200
  edges after: roto on comp #4626 (new id).  M, W: task_template A, comp/lay/roto on A, x, y none
left clean: 0 Shots, Tasks (Shot and template), TaskDependency rows, templates zzprobe_111_*
```

The first run gave the same table (the probe then read 71.8 s, 158 calls, before its call count was cut).
Preconditions: none from an operator. Provisioned by the probe: both templates, the Shots, Tasks and
edges, deleted by `_lib.Created` (edges retire with their Tasks), failure included.

**Teaches**
- **The write back to A applies probe 109's rule: every edge whose downstream Task is A-linked and that
  A lacks is erased**, whatever the upstream end: extra (R1, roto on x), merge-made (R2), or A-linked (roto
  on lay). Pre-merge edges the merge kept (roto on x, roto on lay) are lost by the undo. Edges with only
  the upstream end on A (paint on lay, y on lay) are kept.
- Recipe 022 DELETEs every non-snapshot edge unless both ends go back to A, so a re-created outside edge
  (R1) 404s the batch and nothing lands. Leave out every edge whose downstream end goes back to an A task.
- **A's own roto on comp was re-created with a new id** on both Shots; probe 104, where roto had no other
  upstream edge, kept the id. Recipe 019's step 3 sweep then deleted it, leaving W with no edge at all.
  Which hand edge causes the re-create: not measured.
- Re-create the lost pre-merge edges from a snapshot of ends, type and offset (recipe 016). Doing that
  inside the undo batch: not measured.
