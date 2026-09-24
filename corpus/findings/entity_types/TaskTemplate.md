---
tags: [task-template, task, dependency, destructive]
scope: api
measured: site-wide read of every template and its Tasks, sandbox project written, 7 templates made and deleted
summary: A named set of Tasks a Shot, Asset or other entity can be created with.
verdict: A template's tasks are ordinary Tasks with `task_template` set and `project` null; read them with `["task_template", "is", T]`. Deleting a template retires its tasks.
---

# TaskTemplate

**Type** `TaskTemplate`, addressed at `/entity/task_templates` (`/entity/TaskTemplate` also answers;
`/entity/tasktemplates` is 404 `Entity type 'tasktemplates' does not exist.`). Site-wide: the type has
no `project` field, and `["project", "is", ...]` is 400 `API read() TaskTemplate.project doesn't exist.`

| field | data type | editable | notes |
|---|---|---|---|
| `code` | text | yes | the name; `mandatory` true, `unique` false |
| `entity_type` | entity_type | flagged no | the type the template is for; writable on create and by `PUT` |
| `description` | text | yes | |
| `projects` | multi_entity `['Project']` | yes | the reverse of `Project.task_templates` (probe 088) |
| `task_count` | number | no | read as a **string**, `"10"`; `PUT` is 400 `API update() TaskTemplate.task_count is read only.` |
| `notes`, `open_notes`, `open_notes_count` | | | as on other types |

On the probed site there are 20 templates: 11 for Asset, 6 for Shot, 2 for Level, 1 for Sequence.

**Identity** `code`. It is not unique: the same `code` twice is 201 twice.

**Create** Nothing is required.

| body | result |
|---|---|
| `{}` | 201, `code` reads `"New TaskTemplate <id>"`, `entity_type` null |
| `{"code": ...}` | 201, `entity_type` null |
| `{"code": ..., "entity_type": "Shot"}` | 201 |
| `"entity_type": "Task"` | 201: any type name is accepted, not only the ones a Task can hang off |
| `"entity_type": "Nope"` or `"shots"` | 400 code 104 `Update failed for [TaskTemplate.entity_type]: 'Nope' is not a valid entity type. Valid entity types: 'Asset', 'Shot', ...` (every type on the site) |
| `PUT {"entity_type": "Asset"}` | 200, reads back `"Asset"`, although the schema flags the field not editable |

**The template's tasks** are Task rows. Nothing about them lives on the TaskTemplate row.

| what | where |
|---|---|
| a template's tasks | `POST /entity/tasks/_search` with `["task_template", "is", {"type": "TaskTemplate", "id": T}]` |
| their `project` and `entity` | always null: 222 of 222 on the probed site |
| `task_count` | equals the number of those Tasks on 20 of 20 templates |
| order | `sg_sort_order`; set on 204 of 222 |
| step | `step`; set on 199 of 222 |
| dates | `start_date` and `due_date` null on all 222; `duration` set on 18 |
| people | `task_assignees` and `task_reviewers` set on 5 each |
| status | `sg_status_list` on all 222 (`wtg` 136, `na` 85, `ip` 1 on the probed site) |
| dependencies | `upstream_tasks` and `downstream_tasks` between template tasks, 50 TaskDependency rows, all `finish-to-start-next-day`, `offset_days` null |

A template task is created with `POST /entity/tasks` and `task_template`, and no `project`:

| body | result |
|---|---|
| `{"content": ..., "task_template": T}` | 201, `project` null, `sg_status_list` the default |
| the same plus `project` | 400 code 103 `API create() Invalid Task: a task template may not have a project` |

**Links** `projects` is the template's only outbound link that a client writes (probe 088 for how a
project names its default). The Tasks point in:

| field on Task | on a template task | on a Task generated from it (probe 083) |
|---|---|---|
| `task_template` | the template | null |
| `template_task` | null | the template task it was copied from |

On the probed site 182 Tasks have `template_task` set and none of them has `task_template`. A
`multi_entity` element of `upstream_tasks` or `downstream_tasks` has a fourth key, `template_task_id`,
next to `id`, `name` and `type`.

```
upstream_tasks [{"id": 47120, "template_task_id": 47116, "name": "zzprobe_083_a", "type": "Task"}]
```

**Status** none. TaskTemplate has no status field.

**Traps**
- **`DELETE /entity/task_templates/<id>` retires the template's tasks.** A template task made for the
  test answered 404 `Task: 47113 not found` after its template was deleted, and the 204 names nothing.
- Filter on `task_template` to read a template, never on `project`: a template task has none, so a
  project-scoped Task query never returns one.
- `task_count` is a string. Compare it with `int()` or count the Tasks.
- `entity_type` does not bind: probe 083 applied an `Asset` template to a Shot and it generated Tasks.
