---
tags: [event-log, task-template, task, observe]
endpoints: [POST /entity/<type>/_search, POST /entity/<type>, PUT /entity/<type>/<id>]
phase: observe
scope: api
measured: sandbox project written with generate_event_log_entries True, 2 templates and 2 Shots made and deleted
verdict: A template-generated Task logs like a hand-made one plus a `template_task` change row, `in_create` true, credited to the caller. Filter `attribute_name` `template_task` to find them.
---

# 090_template_task_events

**Q** Which EventLogEntry rows does applying a task template write, and can a consumer tell a
template-generated Task from a hand-made one?

**Endpoint** `POST /entity/event_log_entries/_search ; POST /entity/shots ; PUT /entity/shots/<id>`

**Docs claim** Silent.

**Actual**

```
ApiUser generate_event_log_entries: True (read, not changed)
hand-made Task: 6 rows   _New + Change for color, content, entity, sg_sort_order, sg_status_list
POST /entity/shots with task_template (2 template tasks, 1 dependency)
  the Shot: 8 rows    _New, Change code, sg_status_list, sg_shot_type, sg_latest_vendor_status,
                      task_template (in_create true), tasks x2 (one per generated Task)
  2 generated Tasks: 16 rows   per Task the hand-made six plus template_task;
                      upstream_tasks on one, downstream_tasks on the other
  the generated TaskDependency: 3 rows   _New, Change task, Change dependent_task
  a generated Task's _New: user {"type": "ApiUser", "name": "<script> 1.0"}, session_uuid null
    meta {"type": "new_entity", "entity_type": "Task", "entity_id": <id>}
  template_task change meta: {"type": "attribute_change", "attribute_name": "template_task",
    "in_create": true, "old_value": null, "new_value": {"name": "zzprobe_090_a", "type": "Task",
    "id": <template task>, "valid": "valid", "status": "wtg", "uuid": "<uuid>"}}
  Shot.tasks meta: {"in_create": true, "added": [{"name": "zzprobe_090_a", "type": "Task", ...}], "removed": []}
PUT task_template tt2 on the Shot -> 1 Task added
  the Shot: +1 task_template Change (no in_create), +1 tasks Change with in_create true
  the added Task: 7 rows, the same shape
filter [["attribute_name", "is", "template_task"], ["entity", "in", <the 3 Tasks>]] -> 3
```

**Teaches**

| row | written for |
|---|---|
| `Shotgun_Task_New` + one `Shotgun_Task_Change` per set field | every generated Task, as for a hand-made one |
| `Shotgun_Task_Change` `template_task`, `in_create` true | generated Tasks only |
| `Shotgun_Task_Change` `upstream_tasks` / `downstream_tasks` | each end of a copied dependency |
| `Shotgun_TaskDependency_New` + `task` + `dependent_task` Changes | each copied dependency |
| `Shotgun_Shot_Change` `task_template` | the Shot, on create and on each change |
| `Shotgun_Shot_Change` `tasks`, `in_create` true | the Shot, once per generated Task, on create and on reapply |

- **The generated rows are credited to whoever wrote `task_template`.** `user` is the ApiUser and
  `session_uuid` null, the same as the script's own writes (probe 049). Nothing marks them as the
  server's work.
- **`template_task` is the marker.** The hand-made Task logged no such row, since it leaves
  `template_task` null, and `attribute_name` is filterable, so pair it with `entity` or `event_type` to list template-made Tasks.
  `meta.new_value.id` names the template task each one came from.
- `in_create` is true on the Shot's `tasks` row written during a reapply, although the Shot was not
  being created: it follows the Task's create, so it cannot tell a create-time apply from a reapply.
  The Shot's `task_template` row can: its `meta` has no `in_create` on the `PUT`.
- One apply of a 2-task, 1-dependency template wrote 21 rows beyond the Shot's own 6: per Task 7 rows
  plus one `tasks` row on the Shot, per dependency 3 rows plus one link row on each Task.
- Server-set fields log too: `color` and `sg_status_list` were never sent and each has a row.
