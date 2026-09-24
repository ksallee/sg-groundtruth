---
tags: [task-template, task, duration, trap]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 1 template (6 tasks), 1 Shot (6 Tasks) made and deleted by the probe; 18.0 s, 45 calls
verdict: Re-sync to T: a numeric 0 on T's task overwrites (est, duration); milestone false and "" (stored null) keep the Task's value; a Task with only start or only due keeps its null duration.
---

# 108_task_template_resync_empties

**Q** Probe 102 found that writing an entity's `task_template` to T overwrites a linked Task's field
when T's task holds a value and keeps it when T's is empty. Where do these fall: `milestone` false on
T vs true on the Task; a numeric 0 on T (`est_in_mins`, `duration`); `sg_description` "" vs null on T;
`duration` on T vs a Task with only `start_date`, or only `due_date`, set?

**Endpoint** `PUT /entity/shots/<id> ; PUT /entity/tasks/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent.

**Setup** Provisioned by the probe; no operator step. One template T with six tasks and no edges (no
dependency cascade), one Shot created with T, each linked Task hand-edited, then `task_template`
null, then T (recipe 015's re-apply). Every step read back. All rows deleted; the left-clean check
found 0 Shots, templates, Tasks, template tasks and TaskDependency rows.

**Actual**

```
T as read back:  z milestone False, est 0, desc None ("" was written)
                 n dur 0, desc None, est None     c milestone True, est 300, desc T.c (control)
                 f dur 480 (control)   s dur 960   d dur 960
Task   before the re-apply                          after task_template null   after task_template T
z      milestone True, est 60, desc hand            unchanged                  milestone True, est 0, desc hand
n      dur 1920, est 60, desc hand, no dates        unchanged                  dur 0, est 60, desc hand
c      milestone False, est 60, desc hand           unchanged                  milestone True, est 300, desc T.c
f      dur 1920, no dates                           unchanged                  dur 480
s      start 2026-05-04, due None, dur None         unchanged                  unchanged
d      start None, due 2026-05-08, dur None         unchanged                  unchanged
every PUT -> 200; all six Tasks still linked to T's tasks throughout
```

**Teaches**

| on T's task | on the linked Task | after the re-sync |
|---|---|---|
| `milestone` true (control) | false | overwritten: true |
| `milestone` false | true | **kept: true**. False is the checkbox's empty |
| `est_in_mins` 0 | 60 | **overwritten: 0** |
| `duration` 0 | 1920, no dates | **overwritten: 0** |
| `duration` 480 (control) | 1920, no dates | overwritten: 480 (102 agrees) |
| `sg_description` "" | "hand" | kept. The server stored "" as null on T's task, so "" and null are one case |
| `sg_description` null, `est_in_mins` null (negative control) | a value | kept (102 agrees) |
| `duration` 960 | only `start_date` set, duration null | kept: duration stays null, no date filled |
| `duration` 960 | only `due_date` set, duration null | kept: duration stays null, no date filled |

- **0 is a value, false is not.** A numeric 0 on T's task wipes the Task's number; a false checkbox
  never clears a true one. A merge that means "leave it" must not store 0 on the template.
- **`duration` copies only onto a Task with no dates** (here and in 102). Either date set, alone or
  with the other, keeps the Task's duration; with one date only, it stays null.
- A text field cannot hold "" on a template task: the write is accepted and reads back null.
- Not measured: "" on the linked Task side; `sg_sort_order` 0; a custom number or checkbox field;
  `milestone` false on T vs a Task with dates; duration 0 on T vs a dated Task.
