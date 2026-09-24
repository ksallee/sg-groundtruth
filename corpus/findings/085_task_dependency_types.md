---
tags: [dependency, task, date, create, enumeration]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, GET /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 26 Tasks and their TaskDependency rows made and deleted
verdict: TaskDependency takes four `dependency_type` values, default `finish-to-start-next-day`; `offset_days` counts working days and snaps the dependent both ways. `shift_ratio` moved nothing.
---

# 085_task_dependency_types

**Q** Which `dependency_type` values does a TaskDependency take, and what do the type, `offset_days`
and `shift_ratio` do to the dependent Task's dates?

**Endpoint** `POST /entity/task_dependencies ; PUT /entity/task_dependencies/<id> ; GET /entity/tasks/<id>`

**Docs claim** Silent. The schema types `dependency_type` as plain `text` with no `valid_values`.

**Actual**

```
POST /entity/task_dependencies {"task": D, "dependent_task": U, "dependency_type": "zz_bogus"} -> 400 code 104
  "Create failed for [TaskDependency]: Validation failed: Dependency type Dependency type 'zz_bogus'
   is invalid, accepted values are finish-to-start-next-day, start-to-start, finish-to-finish,
   start-to-finish-next-day."
dependency_type omitted -> 201, stored "finish-to-start-next-day"
null -> 400, the same message with ''     "START-TO-START" -> 400, the same message

{"task": D, "dependent_task": U} -> cached_display_name "Task <D> dependent on Task <U>";
  D.upstream_tasks = [U]

U runs Mon 2026-03-02 .. Fri 2026-03-06; each D starts 2026-02-16, two working days long
  type                      none                 offset_days 2        offset_days -1       shift_ratio 0.5
  finish-to-start-next-day  03-09..03-10         03-11..03-12         03-06..03-09         03-09..03-10
  start-to-start            03-02..03-03         03-04..03-05         02-27..03-02         03-02..03-03
  finish-to-finish          03-05..03-06         03-09..03-10         03-04..03-05         03-05..03-06
  start-to-finish-next-day  02-26..02-27         03-02..03-03         02-25..02-26         02-26..02-27

PUT on a live finish-to-start row: offset_days 3 -> D 03-12..03-13; type start-to-start -> 03-05..03-06;
  offset_days null -> 03-02..03-03
a second row for the same pair -> 400 "... Validation failed: There is already a connection between the entities."
task == dependent_task, or the reverse edge -> 400 "... Can't create this dependency as it causes a loop."
```

**Teaches**

| `dependency_type` | the dependent Task (`task`) is placed so that |
|---|---|
| `finish-to-start-next-day` | it starts the working day after `dependent_task` ends |
| `start-to-start` | it starts the day `dependent_task` starts |
| `finish-to-finish` | it ends the day `dependent_task` ends |
| `start-to-finish-next-day` | it ends the working day before `dependent_task` starts |

- **The field names read backwards.** `task` is the downstream Task and `dependent_task` is the one it
  depends on: the row reads `Task <task> dependent on Task <dependent_task>`, and `task` gets
  `dependent_task` in its `upstream_tasks`.
- `offset_days` is working days on top of the type and may be negative: `finish-to-start-next-day` with 2 moved Monday
  to Wednesday, with -1 it put a start on the upstream's Friday and its end on the next Monday.
- **The dependent snaps to the constraint in both directions.** Every D started two weeks early and was
  moved later; setting `offset_days` back to null moved a D earlier. It is placement, not a minimum.
- `PUT` on a live row reschedules at once, so a type or offset can be corrected in place.
- `shift_ratio` 0.5 was accepted with 201 and changed no date in any of the four types. Its effect is
  unmeasured beyond that.
- The server rejects a duplicate pair, a self-loop and a two-Task cycle with a 400; longer cycles are
  unmeasured. `pinned` stayed false throughout (probe 087 for pinned Tasks).
