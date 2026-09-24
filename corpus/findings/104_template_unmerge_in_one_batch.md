---
tags: [task-template, batch, dependency, destructive]
endpoints: [POST /entity/_batch, PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 2 templates and 4 Shots made and deleted, all provisioned by the probe; 42.0 s, 93 calls
verdict: Recipe 019's undo fits one `_batch` with the same end state, if the batch skips edges its own task_template write removes: deleting one 404s and rolls back all. Undo to null deletes them.
---

# 104_template_unmerge_in_one_batch

**Q** Recipe 019 undoes a template merge with separate calls. Does the same sequence in one `_batch`
leave the same Tasks, links, edges and fields, for an entity that had template A before, and for one
that had none?

**Endpoint** `POST /entity/_batch ; PUT /entity/tasks/<id> ; PUT /entity/shots/<id> ; DELETE /entity/<type>/<id> ; POST /entity/tasks/_search ; POST /entity/task_dependencies/_search`

**Docs claim** Silent.

**Actual**

```
A: comp, roto, lay; roto on comp.  B: comp, lay (same content, step), paint; lay on comp SS+1, paint on lay
X, Y made with A, then comp ip "hand", lay order 99, roto "hand" 1440.  N1, N2: no template, hand comp, lay
all four merged into B (recipe 020 batch) -> 200; Y = X, N2 = N1 (fields, links, edges)
  X: 4 Tasks (+ paint), comp/lay B's order/desc/dur, 3 edges (+ lay on comp SS+1, + paint on lay)
undo X, N1 by recipe 019's calls -> all 200/204; N1's sweep deleted lay on comp (204)
negative control, Y: one batch [2 claims back to A, Shot task_template A, DELETE paint,
  DELETE TaskDependency lay-on-comp (what 019's step 3 read now finds), 3 field writes]
  -> 404 "Entity of type [TaskDependency] with id=4409 does not exist."
  Y re-read: identical to Y merged (task_template B, paint, fields, 3 edges): nothing landed
undo Y, one batch, the edge DELETE left out                       -> 200
undo N2 (to null), one batch [2 claims to null, Shot null, DELETE paint,
  DELETE TaskDependency lay-on-comp, 2 field writes]              -> 200
after
  Y (batch) vs X (calls): identical;  N2 (batch) vs N1 (calls): identical
  X, Y, N1, N2 each vs itself before the merge: identical, same Task ids and edge ids
    X: A, 3 Tasks, comp ip "hand", lay 99, roto "hand" 1440, roto on comp (same edge id)
    N1: null, 2 Tasks, no template_task, no edge
left clean: 0 Shots, 0 Tasks (Shot and template), 0 TaskDependency, 0 templates zzprobe_104_*
```

**Teaches**
- One batch gives the split sequence's end state in both cases measured: no duplicate Task, the old
  `template_task` links, the old edges with their ids, the snapshot's fields, status kept.
- Requests run in order and the `task_template` A write runs its apply mid-batch (probe 098): it
  removes B's edge between the two claimed Tasks. A later DELETE of that edge 404s and rolls back the
  whole batch (recipe 002). Recipe 019's step 3 reads the edges after that write; a batch cannot.
- So read every id before the batch and leave out edges whose two ends go back to a template task of a
  non-null old template. Undo to null: the server removes nothing, keep the DELETE. Mixed ends: not measured.
- A Task DELETE in the batch retires its edges, as a DELETE call does (probe 089): paint on lay went
  with paint in both. Provisioned by the probe; no operator step. Recipe 022 is this as code.
