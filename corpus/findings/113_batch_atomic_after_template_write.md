---
tags: [batch, task-template, error-handling, event-log]
endpoints: [POST /entity/_batch, POST /entity/<type>, DELETE /entity/<type>/<id>, GET /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 1 template, 6 Shots, their Tasks and edges made and deleted by the probe; 52.3 s, 112 calls
verdict: A `_batch` holding a `task_template` apply is atomic: a later or earlier failing request left no Task, no claim, no field write, no edge and no EventLogEntry row.
---

# 113_batch_atomic_after_template_write

**Q** Is a `_batch` atomic when a request fails after a `task_template` write in the same batch?

**Endpoint** `POST /entity/_batch ; POST /entity/task_dependencies ; DELETE /entity/tasks/<id> ; POST /entity/event_log_entries/_search`

**Docs claim** Silent. Recipe 002 measured rollback for plain creates and updates only; a template
apply creates Tasks and edges server-side, inside the same batch.

**Actual**

Template tt: a, b, c; edges b on a, c on b. r: a Task created then DELETEd (retired). One fresh Shot
per case, `description` "before", holding a hand-made a with `sg_description` "before". "bad edge" is
`create TaskDependency {"task": a, "dependent_task": r}`.

| case | batch | status | after, and again 2 s later |
|---|---|---|---|
| a_late | claim a, Shot `task_template` null, Shot tt, a `sg_description` "after", bad edge | 400, 0.8 s | nothing changed |
| b_first | bad edge, claim a, null, tt, a `sg_description` "after" | 400, 0.3 s | nothing changed |
| c_plain | Shot `description` "after", bad edge | 400, 0.4 s | nothing changed |
| d_status | claim a, null, tt, a `sg_status_list` "not_a_status" | 400, 0.9 s | nothing changed |
| e_ok | claim a, null, tt, a `sg_description` "after" | 200, 0.9 s | tt set, a claimed, b and c made, edges b on a and c on b |

```
single POST edge on r -> 400 "Invalid field value, update failed [5 - Update failed for
  [TaskDependency.dependent_task]: Value is not legal.]"   (the same error inside every batch)
d_status -> 400 "Update failed for [Task.sg_status_list]: 'not_a_status' is not a valid status. Valid statuses: ..."
"nothing changed", read back per case:
  Shot task_template None, description 'before'; 1 Task [a]; a template_task None, desc 'before'; edges none
event log rows naming the probe's rows after each failed batch: 0   (3 runs, 12 failed batches)
event log after e_ok: 27 rows: Shot task_template x1, Shot tasks x2, Task_New x2, TaskDependency_New x2,
  Task template_task x3, a sg_description x1, ...
left clean: 0 Tasks, Shots, TaskTemplates zzprobe_113_*, 0 of the edges seen
```

Preconditions: `generate_event_log_entries` on the ApiUser, read and not changed (True on the probed
site). Everything else is provisioned by the probe and deleted by `_lib.Created`, failure included.

**Teaches**
- **The apply rolls back with the batch.** Wherever the failing request sits, a failed batch leaves no
  claim, no `task_template` change, no generated Task or edge and no field write, and writes no
  EventLogEntry row. Recipe 002's rollback holds for server-side work.
- An EventLogEntry row showing an apply means a request that committed. A failed batch did not write
  it; look for a second call (recipe 020 is one batch; any after-apply step is another).
- A `TaskDependency` create naming a retired Task is 400 `Value is not legal.` and takes the batch down.
  Re-read both ends before re-creating an edge.
- The script key is shared: filter the log on your own rows, as other writers land in the same window.
