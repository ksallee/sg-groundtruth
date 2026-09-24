---
tags: [task-template, dependency, destructive]
endpoints: [PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>, POST /entity/<type>/_search, GET /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2 templates and 1 Shot made and deleted by the probe; 43.6 s, 104 calls
verdict: A template write re-syncs every Task linked to it: fields but status reset, edges rewired. Undo: old template_task per Task first, then old task_template, then delete what B made.
---

# 096_task_template_unmerge

**Q** After a merge into template B (recipe 015_apply_task_template_without_duplicates), does writing
the old `template_task` on each claimed Task and the old `task_template` on the entity undo it, and in
which order?

**Endpoint** `PUT /entity/tasks/<id> ; PUT /entity/shots/<id> ; DELETE /entity/tasks/<id> ; POST /entity/task_dependencies/_search`

**Docs claim** Silent.

**Actual**

```
A: comp, roto, lay; roto on comp.   B: comp, lay (same content and step), paint; lay on comp SS+1, paint on lay
Shot made with A, then by hand: comp ip + desc "hand", lay order 99, roto desc "hand" dur 1440
claim comp, lay for B (PUT template_task)  -> 200 each, no field, Task or edge changed
PUT Shot task_template B -> + paint, + lay on comp SS+1, + paint on lay
  comp, lay: order/desc/dur now B's (hand edits gone), comp status ip kept; roto on comp kept
undo 1, Task first
  PUT comp, lay template_task A.*  -> 200 each, nothing else changed (fields stay B's, 3 edges)
  PUT Shot task_template A         -> 200, 4 Tasks, no Task made
    comp, lay, roto: order/desc/dur reset to A's, roto's "hand" and 1440 too; comp status ip kept
    lay on comp SS+1 (B's edge) removed; roto on comp kept, not duplicated; paint on lay kept
  DELETE paint                     -> 204, its edge gone: 3 Tasks, 1 edge, the pre-merge shape
  PUT the pre-merge order/desc/dur on each Task -> 200, the hand edits back: pre-merge state
undo 2, entity first (after merging again)
  PUT Shot task_template A -> 6 Tasks: new comp and lay from A, status wtg
    roto on comp moved: the old edge deleted, roto now on the new comp; B's 2 edges kept
  PUT comp, lay template_task A.* -> 200, nothing merged: two Tasks point at A.comp, two at A.lay
undo 3, to nulls (after merging again)
  PUT comp, lay template_task null; PUT Shot task_template null -> 200, nothing changed
    B's fields and both B edges stay
```

**Teaches**

| write | server does |
|---|---|
| `template_task` on a Task | nothing but that field |
| `task_template` changed to T | for every Task pointing at a T task: `sg_sort_order`, `sg_description`, `duration` set to the template task's; `sg_status_list` kept |
| the same | creates the Tasks no Task points at (probe 084), adds T's missing edges, deletes edges between two T-linked Tasks that T lacks, moves an edge to the Task that now holds its template end |
| `task_template` null | nothing: no field, Task or edge touched |

- **The apply overwrites hand edits.** It re-syncs every linked Task, not only the new ones: `roto`,
  never claimed, lost its description and duration. This corrects probe 084's "skipped" and recipe
  015, which says only `template_task` is written. Status is the one field measured to survive.
- **Order: Tasks first, then the entity.** Entity first, A's apply finds its tasks unclaimed, makes a
  second comp and lay, and moves A's edge onto them. Pointing the originals back afterwards merges nothing.
- Undo to A needs three kinds of write: old `template_task` per claimed Task, old `task_template`,
  `DELETE` per Task B made (its edges retire, probe 089). The apply removes B's edges between claimed Tasks.
- Undo to null gets no server help: delete B's edges between claimed Tasks yourself. Either way, write
  back the hand-edited fields read before the merge; the merge overwrote them and the undo's apply does too.
