---
tags: [task-template, task, dependency, destructive, trap]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2 templates, 2 Shots, their Tasks and edges made and deleted; 35.4 s, 90 calls
verdict: Writing task_template T re-syncs every Task linked to T: T's non-empty values overwrite, status kept, dates and assignees kept or filled if empty; edges between linked Tasks reset to T's.
---

# 102_task_template_resync

**Q** When an entity's `task_template` is written to T, which fields and edges of the Tasks already
linked to T (by `template_task`) does the server rewrite?

**Endpoint** `PUT /entity/shots/<id> ; PUT /entity/tasks/<id> ; PUT /entity/task_dependencies/<id> ; POST /entity/task_dependencies`

**Docs claim** Silent.

**Actual**

```
T: a s1 dates 03-02..03-04 est 600 desc/order/reviewers/assignees G1, list 1_Tier, checkbox True, status na
   b s2 dur 960 est 300 ...  c s3 milestone, order 30, the rest empty.  b on a finish-to-start-next-day, c on b start-to-start 2
Shot1 created with T, then a1 = every field other, b1 = every field empty, c1 = T's empties set
field            a1 other -> after T   b1 empty -> after T   c1 set, T empty -> after T
content          a_renamed -> a        b -> b                c -> c
step             s4 -> s1              None -> s2            s3 -> s3
est_in_mins      60 -> 600             None -> 300           120 -> 120
sg_description   hand -> T.a           None -> T.b           hand -> hand
sg_sort_order    77 -> 10              None -> 20            30 -> 30
sg_priority_1    3_Tier -> 1_Tier      None -> 1_Tier        3_Tier -> 3_Tier      (list, custom)
checkbox field   False -> True         False -> True         True -> True          (custom, T.c False)
task_reviewers   G2 -> G1              [] -> G1              G2 -> G2
task_assignees   G2 -> G2 (kept)       [] -> G1              G2 -> G2
sg_status_list   ip -> ip (kept)       wtg                   ip -> ip (T wtg)
start/due        05-04..05-08 kept     none -> 05-11..05-12  06-01..06-03 -> 06-03..06-03
duration         2400 (dated) kept     None -> 960           1440 -> 0
milestone        False                 False                 False -> True
pinned           False -> False        False -> False        True -> True
(a1 is a root Task, unpinned throughout: its dates are kept by the re-sync, not held by a pin)
(Shot2 a2, no dates, dur 1920 -> 1440; dates none -> 03-02..03-04)
edges before: c1 on b1 finish-to-finish 5 (T: start-to-start 2), b1 on a1 deleted, c1 on a1 (not in T), x1 (unlinked) on a1
PUT Shot1 task_template null -> 200, nothing changed;  PUT T -> 200, no Task made
  b1 on a1 finish-to-start-next-day added; c1 on b1 finish-to-finish 5 deleted, a new start-to-start 2 made; c1 on a1 deleted; x1 on a1 kept (same id)
PUT a1 desc hand2; PUT Shot1 task_template U -> + u; a1 hand2 kept, T's fields and edges untouched
Shot2 created with U (u2), hand-made a2, b2; b2 on a2 start-to-start 3, u2 on a2; claim a2, b2 for T; PUT T
  a2, b2: the same field outcomes as a1, b1; + c2; b2 on a2 start-to-start 3 replaced by finish-to-start-next-day; u2 on a2 kept
edges the apply deleted (c1 on b1, c1 on a1, b2 on a2): GET 404, GET options[return_only]=retired 404
control, b1 on a1 DELETEd by the probe: GET 404, retired 200.  left clean: 0 Shots, templates, Tasks, TaskDependency rows
```

The probe provisions every row it reads. Site state it needs is declared in `requires` and checked
first: 4 Shot Steps, statuses na, wtg, ip, a custom Task list field with 2 values, 2 Groups with no
members (reused, never created). It uses the first custom Task checkbox field when the site has one.

**Teaches**

| on T's task | on the linked Task before | after the write |
|---|---|---|
| a value in `content`, `step`, `est_in_mins`, `sg_description`, `sg_sort_order`, `task_reviewers`, `milestone` | anything | **overwritten with T's**: a renamed Task gets its old name back |
| a value in a custom field: on the probed site one list field and one checkbox field, both behaved as above | anything | overwritten with T's |
| `duration` | a Task without dates | overwritten; a Task with start and due keeps its dates and the duration they give |
| `duration` | only `start_date` or only `due_date` set, duration null | kept: stays null, no date filled (probe 108) |
| a numeric 0: `est_in_mins`, or `duration` on a Task without dates | a value | **overwritten with 0** (probe 108) |
| `start_date`, `due_date` | set / empty | kept / filled, then moved by the dependency cascade (probe 087) |
| `task_assignees` | set / empty | kept / filled |
| `sg_status_list`, `pinned` | anything | kept |
| empty: null, a checkbox's false, a text `""` (stored as null on the template task) | a value | kept: an empty template field never clears (probe 108) |
| edge, T has it | missing / other type or offset, `offset_days` null against 0 included (probe 105) | created / erased and re-created as T's (new id) |
| edge T lacks | both ends linked to T | erased |
| edge T lacks | downstream end linked to T, upstream end not (unlinked, another template, another entity) | **erased** (probes 107, 109) |
| edge T lacks | upstream end linked to T, downstream end not | kept: x1 on a1, u2 on a2 here, w on b in probe 109 |

- **Every write that changes `task_template` to T re-syncs all Tasks already linked to T**, after a
  clear or from another template, and Tasks claimed a moment earlier (recipe 015) the same as Tasks
  T made. Setting milestone collapses the Task to one day at its due date, duration 0.
- Kept dates are the re-sync's, not a pin's: the unpinned root a1 keeps them. The re-sync leaves
  `pinned` as it was. An edge it deletes is erased: 404 under `options[return_only]=retired`.
- Writing another template U or null touches no T-linked Task or edge (probe 096 agrees).
- The edge rows for a Task not linked to T are corrected by probes 107 and 109: this run measured only
  the outside Task downstream (x1, u2), and first read "one end unlinked → kept" for both directions.
- Two Tasks linked to one template task: only one is re-synced and wired, picked unpredictably (probe 106).
- Corrected in probe 084 (it read "only adds", linked Tasks "skipped") and recipe 015 (it read "creates
  only what is missing" and "Only `template_task` is written"). Probe 083 holds.
