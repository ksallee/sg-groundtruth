---
tags: [entity-type, task, create, dependency, duration, status, entity-field, trap]
scope: api
summary: A unit of work on a Shot or an Asset, at one pipeline step.
verdict: A Task is named by `content`, never `code`; a create needs only `project`; `start_date`, `due_date` and `duration` are one triple the server recomputes on every write.
---

# Task

**Type** `Task`, addressed at `/entity/tasks`. Project-scoped: `project` is a stock `entity` field with
`valid_types: ['Project']`, and a create without it is refused. The slug is lenient. `GET /entity/task`
and `GET /entity/Task` both answer 200 with `"type": "Task"` and `links.self` of
`/api/v1/entity/tasks/<id>`; an unknown type is `404 Entity type 'zzznope' does not exist.`

**Identity** `content`, a `text` field and the only one the schema flags `mandatory`. Task has no `code`
and no `name` field, and asking for one is a 400, not an empty result.

| filter | result |
|---|---|
| `["content", "is", "<task name>"]` | matches |
| `["cached_display_name", "is", "<task name>"]` | matches, the same rows |
| `["code", "is", ...]` | 400 `API read() Task.code doesn't exist.` |
| `["name", "is", ...]` | 400 `API read() Task.name doesn't exist.` |

`cached_display_name` is a copy of `content` and is server-managed. The schema marks it editable, a PUT
to it returns 200 and changes nothing, and when `content` is null it reads `"-"`.

**Create** `project` alone. The schema's `mandatory` on `content` is not the create contract (probe 012).

| body | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `content` alone | 400, the same title with the body echoed |
| `entity` alone, `content` + `entity` | 400, the same title |
| `project` alone | 201, `content` reads `"New Task <id>"` |
| `project` + `content` | 201 |
| `project` + `entity` | 201, `content` reads `"New Task <id>"` |
| `project` + `content` + `entity` + `step` | 201 |

**Links** `entity` is what the Task hangs off and `step` is its pipeline step. Both read under
`relationships` with the linked row's display name (`field_types/entity`).

| field | type | editable | `valid_types` |
|---|---|---|---|
| `entity` | entity | yes | `Asset`, `Level`, `MocapSetup`, `MocapTake`, `MocapTakeRange`, `ShootDay`, `Shot`, `Sequence` |
| `step` | entity | yes | `Step` |
| `project` | entity | yes | `Project` |
| `task_assignees`, `task_reviewers` | multi_entity | yes | `Group`, `HumanUser` |
| `upstream_tasks`, `downstream_tasks` | multi_entity | yes | `Task` |
| `sibling_tasks` | multi_entity | no | `Task` |
| `template_task` | entity | yes | `Task` |
| `task_template` | entity | yes | `TaskTemplate` |
| `notes`, `tags`, `addressings_cc` | multi_entity | yes | `Note`, `Tag`, `Group`+`HumanUser` |
| `sg_versions`, `open_notes` | multi_entity | no | `Version`, `Note` |

A client filters on `entity`, by hash or by dotted path; a bad value returns 0 rather than an error.

| filter | matches |
|---|---|
| `["entity", "is", {"type": "Shot", "id": N}]` | the Tasks on that Shot |
| `["entity", "type_is", "Shot"]` | every Task on a Shot |
| `["entity.Shot.code", "is", "sh010_0010"]` | the same rows, without the id lookup |
| `["step", "is", {"type": "Step", "id": N}]` | the Tasks at that step |
| `["step.Step.short_name", "is", "CMP"]` | the same rows; `"ZZNOPE"` returns 0 |

**Scheduling** `start_date`, `due_date` and `duration` are one triple: write any part and the server
recomputes the rest over working days. `duration` is minutes, and the working day is `hours_per_day`
from `GET /preferences` (`field_types/duration`). On the probed site `hours_per_day` is `8.0`, which is
why a Monday-to-Friday span reads back as `2400`.

| PUT | reads back |
|---|---|
| `start_date` 2026-01-05, `due_date` 2026-01-09 | `duration` 2400 |
| `duration` 480 | `due_date` 2026-01-05, `start_date` held |
| `duration` 2400 | `due_date` 2026-01-09 |
| `start_date` 2026-02-02 | `due_date` 2026-02-06, `duration` 2400 held |
| `due_date` 2026-02-13 | `duration` 4800, `start_date` held |
| `est_in_mins` 600 | `time_vs_est` 600, which is `est_in_mins - time_logs_sum` |
| `time_logs_sum` 60 | 400 `API update() Task.time_logs_sum is read only.` |
| `time_vs_est` 60, `time_percent_of_est` 50 | 400, the same title per field |
| `duration` `"2 days"` | 400 `Invalid data for 'duration' data type. Value: 2 days` |

**Dependencies** are exposed, two ways. `upstream_tasks` and `downstream_tasks` are editable
`multi_entity` of `Task` and are two views of one link: PUT `upstream_tasks: [B]` on A, and A reads back
under B's `downstream_tasks`. Clearing from either side clears both. The join row is a site-wide entity
of its own at `/entity/task_dependencies`, with `task` and `dependent_task` (`entity`, `['Task']`),
`dependency_type` (`text`), `offset_days` (`number`), `shift_ratio` (`float`), the read-only
`task_id`/`dependent_task_id`, and no `project` field.

```
GET /entity/task_dependencies?fields=<all>
 {"cached_display_name": "Task 5742 dependent on Task 5741", "dependency_type":
  "finish-to-start-next-day", "dependent_task_id": 5741, "offset_days": null,
  "shift_ratio": null, "task_id": 5742}
 relationships: {"dependent_task": {"id": 5741, "type": "Task"}, "task": {"id": 5742, "type": "Task"}}
```

Linking reschedules. Writing `upstream_tasks` moved the dependent's `start_date` to the day after the
upstream `due_date` and held its `duration`. Writing an earlier date on the dependent afterwards
returned 200, set `dependency_violation` to true and flipped `pinned` to true.

| write | result |
|---|---|
| `sibling_tasks`, `dependency_violation` | 400 `API update() Task.sibling_tasks is read only.` |
| filter `["sibling_tasks", "is_not", null]` | 400 `Read failed for entity type [Task]`, no `source` |
| filter `["upstream_tasks", "is_not", null]` | accepted, 200 |

**Status** `sg_status_list`, a `status_list`. Read the usable set for one project from
`GET /schema/Task/fields/sg_status_list?project_id=N` and subtract `hidden_values` from `valid_values`
yourself (probe 009, `field_types/status_list`); `default_value` is what a create without the field
gets. The codes are site configuration, not part of the type.

**Traps**
- Identity is `content`. `code` and `name` do not exist on Task and both 400, so a generic
  "read the `code`" client fails on this type alone.
- `content` is `mandatory` in the schema and still nullable over REST: `null` and `""` both return 200
  and read back `null`, leaving `cached_display_name` as `"-"`.
- `valid_types` on `entity` does not bind, matching `field_types/entity`. `{"type": "Task", "id": N}`
  was accepted at 200 and read back as a Task.
- Never PUT two of `start_date`, `due_date`, `duration` expecting both to stand: the third is recomputed,
  and on a dependent Task a date write also sets `pinned` and can raise `dependency_violation`.
- `time_logs_sum`, `time_vs_est` and `time_percent_of_est` are read only. Sum `TimeLog.duration` to
  predict them; `Task.color` is not a colour either (`field_types/color`).
