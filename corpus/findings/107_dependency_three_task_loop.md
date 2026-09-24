---
tags: [dependency, task-template, batch, destructive]
endpoints: [POST /entity/<type>, POST /entity/_batch, PUT /entity/<type>/<id>, POST /entity/<type>/_search, GET /entity/<type>/<id>, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 1 template, 4 Shots, 12 Tasks and their edges made and deleted by the probe; 34.6 s, 90 calls
verdict: A three-Task loop is a 400 on a direct create and inside `_batch`, which rolls back whole. A template apply deletes a claimed Task's upstream edge from a Task outside the template, loop or not.
---

# 107_dependency_three_task_loop

**Q** Is a three-Task TaskDependency loop (a -> b -> c -> a) refused on a direct create, inside one
`_batch`, and when a template apply's edge would close it?

**Endpoint** `POST /entity/task_dependencies ; POST /entity/_batch ; PUT /entity/shots/<id> ; POST /entity/task_dependencies/_search ; GET /entity/task_dependencies/<id>`

**Docs claim** Silent. Probe 085 measured the self-loop and the two-Task loop only.

**Actual**

```
(1) direct: POST q on p -> 201, POST r on q -> 201, POST p on r -> 400
    [{"status": 400, "code": 104, "title": "Create failed for [TaskDependency]: Can't create this
      dependency as it causes a loop.", "source": null, "detail": null, "meta": {"crud_error_uuid": ...}}]
    edges read back: q on p, r on q
(2) _batch [t on s, u on t, s on u] -> 400, the same title;  edges among s, t, u: none
    control _batch [t on s, u on t] -> 200;  edges: t on s, u on t
    then POST s on u -> 400, the same title
(3) template a, b; edge b on a finish-to-start-next-day. Hand-made a, b (claimed), x (outside the template)
  loop Shot, pre edges x on b, a on x (b on a would close b -> a -> x -> b)
    after _batch claim a, b -> 200:  a on x, x on b
    after PUT task_template=null -> 200:  a on x, x on b
    after PUT task_template=tt -> 200:  b on a (new), x on b
    pre a on x: GET -> 404, options[return_only]=retired -> 404;  pre x on b: GET -> 200
    upstream_tasks: a=[], b=[a], x=[b];  Shot.task_template = tt
  control Shot, pre edge a on x only (no loop possible)
    after claim, after PUT null:  a on x
    after PUT task_template=tt -> 200:  b on a (new)
    pre a on x: GET -> 404, retired -> 404;  upstream_tasks: a=[], b=[a], x=[]
left clean: 0 Tasks, Shots, TaskTemplates zzprobe_107_*, 0 of the edges seen
```

Preconditions: none from an operator. The probe provisions every row it reads and deletes them.

**Teaches**
- The loop check follows the whole chain: closing a three-Task cycle is the same 400 as the two-Task
  case (probe 085). Inside `_batch` it counts rows the same batch created earlier, and the batch rolls
  back with no row left (recipe 002).
- **A template apply never closed the loop because it had already deleted a leg.** The `PUT
  task_template` erased `a on x`, where a claimed Task depends on a Task outside the template, in the
  control Shot too, where no loop was possible. No error; the row reads 404 under
  `options[return_only]=retired`, as in probe 101.
- The reverse, `x on b` (the outside Task downstream of a claimed one), was kept, as probes 101 and 102
  found. **Probe 102's row "one end unlinked → kept" holds only for that direction.** Read a claimed
  Task's `upstream_tasks` before the apply and re-create the edges it should keep.
- Not measured: a claimed Task that has an upstream in the template (here `b`) depending on an outside
  Task, and a loop the apply could close without deleting a leg.
