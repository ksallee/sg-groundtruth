---
tags: [task-template, batch, trap]
endpoints: [DELETE /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>/<id>, PUT /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project, 1 template and 4 Shots made and deleted by the probe; 32.7 s wall, 89 calls
verdict: Revive restores `template_task`. A task_template write while the Task is retired re-creates it, so a later revive leaves two Tasks on one template task. Revive first, then write.
---

# 110_template_task_after_revive

**Q** A Task generated from template A is deleted, by `DELETE` and by a `_batch` `delete`, then revived.
Is its `template_task` restored? And if the Shot's `task_template` is written to A while the Task is
retired, does the apply make a new Task for that template task, leaving two after the revive?

**Endpoint** `DELETE /entity/tasks/<id> ; POST /entity/_batch ; POST /entity/tasks/<id>?revive=1 ; PUT /entity/shots/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent.

**Actual**

```
A: x, y; y on x finish-to-start-next-day. One Shot per route and order, made with A -> X (A.x), Y (A.y)
template write = PUT task_template null, then A (the apply runs only on a change, probe 084)
DELETE, template first
  created           2 Tasks [X->A.x, Y->A.y]            edges [Y on X#4497]
  DELETE X -> 204   1 Task  [Y->A.y]                    edges []
    X under return_only retired: listed, template_task=A.x
  template write    2 Tasks [Y->A.y, new->A.x]          edges [Y on new#4498]
  revive X -> 200   3 Tasks [X->A.x, Y->A.y, new->A.x]  edges [Y on X#4497, Y on new#4498]
DELETE, revive first
  DELETE X -> 204   1 Task  [Y->A.y]; X retired with template_task=A.x
  revive X -> 200   2 Tasks [X->A.x, Y->A.y]            edges [Y on X#4499] (same id)
  template write    2 Tasks [X->A.x, Y->A.y]            edges [Y on X#4499]: nothing made
_batch delete, template first  (200 did_delete true)   identical to DELETE, template first:
  template write makes new->A.x with edge Y on new; revive -> 3 Tasks, A.x twice, 2 edges into Y
_batch delete, revive first                             identical to DELETE, revive first
left clean: 0 Tasks zzprobe_110* (template tasks included), 0 TaskDependency on the 12 Tasks seen,
  0 templates, 0 Shots
```

**Teaches**
- **Revive restores `template_task`**, on both delete routes. The retired row keeps it: a `_search`
  with `return_only: retired` reads `template_task` A.x before the revive.
- **A retired Task does not count as linked.** The apply re-creates its template task (probe 084's
  match key) and copies the template edge onto the copy. Reviving the original afterwards gives two
  Tasks on A.x, and Y then depends on both, by two edges.
- **Order: revive, then the template write.** Revived first, the Task is linked again and the apply
  makes nothing. `_batch` takes no revive (recipe 021), so an undo revives by separate calls before
  its batch (recipe 022).
- Measured with null -> A only. The B -> A write of an undo (probes 096, 104) was not measured here,
  nor a Task retired from a template other than the one written.

The probe provisions every row; no operator step. Y's Task is the negative control: live throughout,
never duplicated in any of the four runs.
