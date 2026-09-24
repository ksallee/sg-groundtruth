---
tags: [batch, dependency, task, create, silent]
endpoints: [POST /entity/_batch, POST /entity/<type>, GET /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 13 Tasks and their TaskDependency rows made and deleted
verdict: Tasks and their dependencies take two `_batch` calls: create the Tasks, then create TaskDependency rows. `upstream_tasks` on a create links without rescheduling.
---

# 086_batch_tasks_with_dependencies

**Q** Can one `_batch` create Tasks and link them to each other? If not, what is the fewest calls,
and does each route schedule the dependents?

**Endpoint** `POST /entity/_batch ; POST /entity/tasks ; GET /entity/tasks/<id>`

**Docs claim** Silent on dependencies, and on whether a batch can create a TaskDependency.

**Actual**

```
one batch: create x1, create x2 with upstream_tasks [{"type": "Task", "id": "$0"}]
  -> 400 code 104 "Invalid field value, update failed [5 - Update failed for [Task.upstream_tasks]:
     Value is not legal.]"          id -1: the same.  Tasks left on the Shot: 0

route 1  batch 1: 4 Task creates, each 2026-03-02..03-03     -> 200 in 0.9s
         batch 2: 3 TaskDependency creates                    -> 200 in 0.4s
           a2 on a1 start-to-start offset_days 1, a3 on a2 (type omitted), a4 on a3 finish-to-finish
         a1 03-02..03-03  a2 03-03..03-04  a3 03-05..03-06  a4 03-05..03-06
         rows read back: (start-to-start, 1), (finish-to-start-next-day, None), (finish-to-finish, None)
route 2  batch 2: 2 Task updates of upstream_tasks            -> 200 in 0.6s
         b1 03-02..03-03  b2 03-04..03-05  b3 03-06..03-09    both rows finish-to-start-next-day
route 3  batch: 2 Task creates with upstream_tasks [c1]       -> 200
         c1 03-02..03-03  c2 03-02..03-03  c3 03-02..03-03    rows: 2 x finish-to-start-next-day
         dependency_violation [False, False, False]  pinned [False, False, False]
         the same body as a plain POST /entity/tasks: c4 03-02..03-03
         a later PUT of an unrelated field on c2: dates unchanged
rollback batch: one good TaskDependency, one closing a loop
  -> 400 "Create failed for [TaskDependency]: Can't create this dependency as it causes a loop."
     rows among the Tasks: 3 before, 3 after
```

**Teaches**

| route | calls | dependency type | dependents scheduled |
|---|---|---|---|
| one batch with a placeholder id | 1 | n/a | 400, nothing created |
| Task creates, then `TaskDependency` creates | 2 | any, with `offset_days` | **yes** |
| Task creates, then `upstream_tasks` updates | 2 | `finish-to-start-next-day` only | yes |
| level by level, `upstream_tasks` in the create body | one per level | `finish-to-start-next-day` only | **no** |

- **A link made at create time does not schedule.** `upstream_tasks` in a create body, batched or not,
  writes the TaskDependency row and leaves the dates as sent, with `dependency_violation` false. A later
  write to another field does not fix them. Write the link as a separate update or row.
- `"entity": "TaskDependency"` is a valid batch entity, so route 1 is the one that takes a type and an
  offset: it is how to copy a template's edges (probe 085 for what each type does).
- A loop in a dependency batch rolls the whole batch back like any other failure (recipe 002).
- Recipe 016_create_tasks_with_dependencies is route 1 as code.
