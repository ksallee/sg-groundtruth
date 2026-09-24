---
tags: [task-template, task, dependency, create, shot]
endpoints: [POST /entity/<type>, POST /entity/_batch, GET /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 2 templates and 4 Shots made and deleted
verdict: A create with `task_template` makes the Tasks inside the same call, by `POST` and by `_batch`, copying every field set on the template tasks and their dependency types and offsets.
---

# 083_task_template_on_create

**Q** Does creating a Shot with `task_template` generate Tasks, and what does each Task copy?

**Endpoint** `POST /entity/shots ; POST /entity/_batch ; POST /entity/tasks/_search ; POST /entity/task_dependencies/_search`

**Docs claim** Silent. The REST reference lists `task_template` as an `entity` field on Shot and says
nothing about it generating anything.

**Actual**

```
template: 3 tasks, a -> b start-to-start offset_days 2, b -> c finish-to-start-next-day
  a  step=Animation    status=na  order=10 dur=960  est=600 description, assignee Group
  b  step=Character FX status=wtg order=20 dur=0    milestone (duration 480 sent, read back 0)
  c  step=Comp         status=wtg order=30 2026-03-02..2026-03-04 dur=1440

POST /entity/shots {"project", "code", "task_template": T} -> 201 in 1.4s
  201 body: task_template {"id": 122, ...}, tasks []
  Tasks on the Shot, read at once: 3
    b  step=Character FX template_task=<b> status=wtg order=20 dur=0
    a  step=Animation    template_task=<a> status=na  order=10 dur=960 est=600 assignee Group
    c  step=Comp         template_task=<c> status=wtg order=30 2026-03-02..2026-03-04 dur=1440
  every Task: project=sandbox, task_template null, pinned False
  dep b on a  start-to-start          offset_days 2    shift_ratio null
  dep c on b  finish-to-start-next-day offset_days null
  5s later: 3 Tasks
POST /entity/_batch, the same create                 -> 200, 3 Tasks
POST /entity/shots with an entity_type Asset template -> 201, 1 Task
POST /entity/shots with "task_template": null         -> 201, 0 Tasks
```

**Teaches**

| on the template task | on the generated Task |
|---|---|
| `content`, `step`, `sg_sort_order`, `sg_status_list` | copied |
| `duration`, `est_in_mins`, `sg_description`, `milestone` | copied |
| `task_assignees` | copied |
| `start_date`, `due_date` | copied as the same calendar dates, not shifted |
| a TaskDependency with `dependency_type` and `offset_days` | a new TaskDependency between the new Tasks, same type and offset |
| the template task itself | `template_task` points at it |
| `task_template` | null on the generated Task; the Shot holds it |
| `project`, `entity` | the Shot's project, the Shot |

- The Tasks exist before the 201 returns: a read straight after the create found all three, and one 5s
  later found the same three. There is no background job to poll for.
- The 201 body's `tasks` relationship is `[]` although the Tasks exist. Read them with
  `["entity", "is", <the Shot>]` on `/entity/tasks/_search`, not off the create response.
- `_batch` applies the template exactly as `POST` does. Recipe 002's rule still holds: the batch cannot
  name the Tasks it generates, so read them back afterwards.
- `entity_type` on the template is not checked: an `Asset` template on a Shot create generated its Task.
- Dates copy verbatim. A template task dated in March makes a March Task on every entity, whatever day
  it is created; schedule them afterwards (probe 087 for what a date write then moves).
- Reapplying to a Shot that already has Tasks is probe 084.
