---
tags: [dependency, task-template, destructive]
endpoints: [POST /entity/<type>, POST /entity/_batch, PUT /entity/<type>/<id>, POST /entity/<type>/_search, GET /entity/<type>/<id>, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2 templates, 6 Shots, 16 Tasks and their edges made and deleted by the probe; 45.7 s, 116 calls
verdict: A template apply erases an edge where a linked Task depends on a Task not linked to the template (root or not, other template, other Shot); it kept the edge with the outside Task downstream.
---

# 109_template_apply_outside_edge

**Q** On a template apply, which edges between a Task linked to the template T and a Task not linked
to T does the apply delete?

**Endpoint** `POST /entity/_batch ; PUT /entity/shots/<id> ; POST /entity/task_dependencies/_search ; GET /entity/task_dependencies/<id> ; DELETE /entity/task_dependencies/<id>`

**Docs claim** Silent. Probe 102 said "one end unlinked → kept"; probe 107 found `a on x` (claimed root
upstream from an outside Task) erased and `x on b` (outside Task downstream) kept.

**Actual**

Template tt: a, b; edge b on a (finish-to-start-next-day), so a is the root. Template tt2: y. One Shot
per case: hand-made a, b claimed to tt (`_batch` of `template_task` updates -> 200), one outside Task,
one hand-made edge; then `PUT /entity/shots/<id> {"task_template": tt}` -> 200 in every case.

| case | outside Task | edge | after the PUT | GET | retired |
|---|---|---|---|---|---|
| up_nonroot | x, same Shot, unlinked | b on x #4477 (b has a template upstream) | erased | 404 | 404 |
| other_tpl | y, same Shot, `template_task` = tt2's y | a on y #4481 | erased | 404 | 404 |
| other_shot | z, on another Shot, unlinked | a on z #4485 | erased | 404 | 404 |
| ctl_down | w, same Shot, unlinked | w on b #4487 | kept | 200 | 404 |
| ctl_up | v, same Shot, unlinked | a on v #4489 | erased | 404 | 404 |

```
every case, edges after the PUT: b on a (new), plus w on b in ctl_down only
outside Tasks after the PUT: x, y, z, w, v all GET -> 200; y keeps template_task = tt2's y
ctl_down control for the retired read: DELETE #4487 -> 204, then GET options[return_only]=retired -> 200
edges read after the claim, before the PUT: the hand-made edge only, in every case
left clean: 0 Tasks, Shots, TaskTemplates zzprobe_109_*, 0 of the edges seen
```

Preconditions: none from an operator. Provisioned by the probe: both templates, the Shots, Tasks and
edges, deleted by `_lib.Created`, failure included.

**Teaches**
- **Measured rule: an edge whose downstream end is a Task linked to T and whose upstream end is not
  linked to T is erased by the apply.** It held for a root (a) and a non-root (b), for an unlinked Task,
  a Task linked to another template, and a Task on another entity. The claim alone did not touch it;
  the `PUT task_template` did.
- An edge whose upstream end is linked to T and whose downstream end is not (w on b) was kept, as in
  probes 101, 102 and 107. One case only.
- Erased, not retired: 404 under `options[return_only]=retired`, where an edge the caller DELETEs reads
  200 (control in this run; probe 101 too). No error, no row to recover. Read each linked Task's
  `upstream_tasks` before the apply and re-create the edges to keep.
- Probe 102's "one end unlinked or linked to another template → kept" holds only for the downstream
  direction.
- Not measured: an outside Task upstream of a Task the apply creates (no edge to that Task can exist
  before the apply makes it); an outside Task downstream of a root; outside edges on a re-apply of the
  same template.
