---
tags: [task-template, dependency, trap]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 4 Shots and 9 Tasks per run, 6 runs; committed probe 34.3-35.1 s, 87 calls
verdict: With two Tasks linked to one template task, an apply re-syncs and wires only one of them, picked unpredictably (not by id, age or edges); the other is left as is. No error, nothing duplicated.
---

# 106_template_task_linked_twice

**Q** Two Tasks on one Shot both point `template_task` at the same template task X (a conflict loser
left linked). When the Shot's `task_template` is cleared then set to T (recipes 015, 020), are both
re-synced (probe 102), is anything created, which one gets T's edges to X's neighbours, and does
anything error?

**Endpoint** `POST /entity/tasks ; PUT /entity/shots/<id> ; POST /entity/tasks/_search ; POST /entity/task_dependencies/_search`

**Docs claim** Silent.

Every precondition is provisioned by the probe (template, Shots, Tasks, edges); no operator step.

**Actual**

```
T: w, x (est 600, desc T.x), y; x on w, y on x finish-to-start-next-day
xa, xb: both POSTed with template_task=T.x, est 60, desc hand; xa first (lower id)
Shot1 xa, xb only.  Shot2 the same, xb created_at 2020 and sorting first by content.
Shot3 control: one Task x1.  Shot4 xa, xb, plus w, y linked to T.w, T.y; y on xb, xb on w made by hand
every Shot: PUT task_template null -> 200, nothing changes; PUT task_template T -> 200
run 3 (committed probe), after T:
  Shot1  xa content=x est=600 desc=T.x | xb x_b 60 hand   + w, y created   xa on w, y on xa
  Shot2  xb content=x est=600 desc=T.x | xa x_z 60 hand   + w, y created   xb on w, y on xb
  Shot3  x1 content=x est=600 desc=T.x                    + w, y created   x1 on w, y on x1
  Shot4  xb content=x est=600 desc=T.x | xa x_a 60 hand   nothing created  y on xb, xb on w kept (same ids)
the re-synced one, 6 runs (the first 2 from a draft with the same calls; run 1 had no Shot4):
  Shot1 (xa lower id, older)           xa xa xa xb xb xb
  Shot2 (xb older, earlier by name)    xa xa xb xa xb xb
  Shot4 (edges already on xb)           - xb xb xa xb xb
Shot4 when xa was picked (run 4):
  xa content=x est=600; edges: y on xa, xa on w created; y on xb deleted; xb on w kept
left clean, every run: 0 Tasks, Shots, TaskTemplates zzprobe_106*, 0 of the TaskDependency rows seen live
```

**Teaches**
- **One Task per template task is re-synced and wired, the others are skipped.** The skipped one keeps
  its content and fields, still points at X, and gets no edge. No second X is created; w and y are
  created only when nothing links to them. Every PUT is 200.
- **Which one wins is not predictable from the caller's side.** Across 6 runs the pick flipped on
  identical setups: not the lowest id, not the oldest `created_at`, not the first by `content`, and
  not the Task already holding T's edges (Shot4 run 4).
- When the other Task wins, the loser's edges, both of T's shape, are handled unevenly: `y on xb`
  was deleted, `xb on w` was kept, and the winner got both. Measured once; the cause is not measured.
- Before an apply, leave at most one Task per template task linked: unlink or re-point the others
  (`template_task` null), or the result depends on the server's pick. Recipe 015's key caveat can
  produce this state (probe 096 made it by hand).
