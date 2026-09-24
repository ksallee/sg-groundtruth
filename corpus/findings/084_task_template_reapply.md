---
tags: [task-template, shot, trap]
endpoints: [PUT /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>, DELETE /entity/<type>/<id>, GET /schema/<Type>/fields/<field>, GET /spec.<format>]
phase: write
scope: api
measured: sandbox project written, 2 overlapping templates and 4 Shots made and deleted
verdict: Changing `task_template` to T creates a Task per T task no Task links by `template_task`, duplicating a same-name hand-made one, and re-syncs the linked Tasks' fields and edges (probe 102).
---

# 084_task_template_reapply

**Q** What does setting `task_template` on a Shot that already has Tasks do: add, duplicate, remove,
or nothing? Is there a mode?

**Endpoint** `PUT /entity/shots/<id> ; POST /entity/_batch ; POST /entity/tasks/_search`

**Docs claim** Silent. `/spec.json` mentions `task_template` twice, both in sample records, and
`TaskTemplate` never.

**Actual**

```
tt1: same@Animation, moved@Character FX, only1@Comp      tt2: same@Animation, moved@Comp, only2@FX
Shot A created with tt1; `same` set to ip; one hand-made Task added   -> 4 Tasks
PUT task_template tt2        -> 200, 7 Tasks: + only2, + moved@Comp, + same@Animation (status wtg)
                                 the tt1 Tasks stay, `same` keeps ip, the hand-made one stays
PUT task_template tt2 again  -> 200, 7 Tasks, nothing added
PUT task_template tt1        -> 200, 7 Tasks, nothing added
PUT task_template null       -> 200, 7 Tasks, Shot.task_template null
Shot B bare, hand-made same@Animation, PUT tt1 -> 4 Tasks: the hand-made `same` and a second `same`
Shot C created with tt1, _batch update to tt2  -> 6 Tasks, as the PUT
Shot D created with tt1, generated only1 deleted, PUT null, PUT tt1 -> only1 re-created, 3 Tasks
Shot E created with tt1, generated only1 deleted, PUT tt1 unchanged -> 200, 2 Tasks, nothing made
PUT {"task_template": tt2, "task_template_mode": "replace"}
  -> 400 code 103 "API update() Shot.task_template_mode doesn't exist." (nothing applied)
Shot.task_template schema properties: default_value, summary_default, valid_types
```

**Teaches**

| on the Shot already | the new template's task | result |
|---|---|---|
| nothing | any | created |
| a Task whose `template_task` is this template task | the same | not re-created; **re-synced** to it, fields and edges (probe 102) |
| a Task made from another template, same `content` and `step` | this one | **created: a duplicate** |
| a Task made from another template, same `content`, other `step` | this one | created |
| a hand-made Task, same `content` and `step` | this one | **created: a duplicate** |
| a Task from the old template the new one lacks | none | kept |

- **The match key is `template_task`, not `content` and `step`.** A template task is not re-created only
  when a Task on the entity already points at it. Delete that Task and the next apply re-creates it.
- **No Task is ever removed.** Switching templates, and clearing the field, leave every Task in place,
  statuses and all. A replace means the caller deletes the Tasks itself (probe 089 for what that breaks).
- **It does not only add.** The Tasks linked to the new template have their fields overwritten and the
  edges between them reset to the template's (probes 096, 102 correct this entry's first reading).
- The apply runs only when the value changes. Sending the stored value again added nothing on Shot E
  although a Task was missing; clear the field first, then set it, as Shot D did.
- There is no mode. No body key, schema property or documented parameter selects keep, replace or merge.
  To merge by `content` and `step`, point each matching Task's `template_task` at its template task
  first, then write `task_template` (recipe 015_apply_task_template_without_duplicates).
