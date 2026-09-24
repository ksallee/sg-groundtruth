---
tags: [dependency, task, date, multi-entity, destructive]
endpoints: [DELETE /entity/<type>/<id>, PUT /entity/<type>/<id>, POST /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search, GET /entity/<type>/<id>, GET /schema/<Type>/fields]
phase: write
scope: api
measured: sandbox project written, 1 Shot, 10 Tasks and their edges; 32.9 s wall, 89 calls
verdict: Remove an edge with `DELETE` on its TaskDependency row: revive restores its type and offset. A `remove` on `upstream_tasks` or `downstream_tasks` erases the row for good.
---

# 095_dependency_remove_undo

**Q** Which call removes one dependency between two Tasks, what does that do to the downstream Task's
dates, `pinned` and `dependency_violation`, and can the edge be revived with its `dependency_type` and
`offset_days`, or must it be re-created?

**Endpoint** `DELETE /entity/task_dependencies/<id> ; PUT /entity/tasks/<id> ; POST /entity/task_dependencies/<id>?revive=1 ; POST /entity/task_dependencies ; POST /entity/task_dependencies/_search`

Provisioned by the probe, no operator step: it makes the Shot, the Tasks and every edge, and deletes
them; a read-back after the run finds no Task, Shot or live TaskDependency row left.

**Docs claim** Silent. The schema lists `upstream_tasks` and `downstream_tasks` as editable `multi_entity`
fields and says nothing about the rows behind them.

**Actual**

```
Task fields with valid_types Task: upstream_tasks, downstream_tasks (multi_entity, editable); sibling_tasks (not editable)
late control: u2 03-02..03-06; l1..l4 written 03-23..03-24, l2 and l4 PUT pinned=true, then each edge POSTed
  l1 finish-to-finish +1          -> 03-06..03-09 pinned=False violation=False   (pulled back)
  l2 finish-to-finish +1          -> 03-23..03-24 pinned=True  violation=False
  l3 finish-to-start-next-day +2  -> 03-11..03-12 pinned=False violation=False   (pulled back)
  l4 finish-to-start-next-day +2  -> 03-23..03-24 pinned=True  violation=False
up 03-02..03-06; d finish-to-finish +1, g finish-to-start-next-day +2, e start-to-start +1, f finish-to-start-next-day +2
d written 02-23..02-24 -> pinned=True violation=True       g 03-11..03-12  e 03-03..03-04  f 03-11..03-12
remove  DELETE row d -> 204, DELETE row g -> 204
        PUT e {"upstream_tasks": {"multi_entity_update_mode": "remove", "value": [up]}} -> 200
        PUT up {"downstream_tasks": {"multi_entity_update_mode": "remove", "value": [f]}} -> 200
        GET all four rows -> 404;  _search return_only retired: [(d, finish-to-finish, 1), (g, finish-to-start-next-day, 2)]
        d 02-23..02-24 pinned=True violation=False   g, e, f dates unchanged
PUT up due 03-13 -> d, g, e, f unchanged
revive  POST row d ?revive=1 -> 200 {"did_revive": true}   row g -> the same
        row e, row f -> 404 "Entity of type [TaskDependency] with id=<id> does not exist."
        rows read back: (finish-to-finish, 1), (finish-to-start-next-day, 2), same ids
        d 02-23..02-24 pinned=True violation=True     g 03-18..03-19 (rescheduled from up's 03-13)
re-create  DELETE rows d, g again; PUT up due 03-20 while unlinked
        POST row d finish-to-finish +1 -> 201 new id   d 02-23..02-24 pinned=True violation=True
        POST row g finish-to-start-next-day +2 -> 201   g 03-25..03-26
        PUT e upstream_tasks add [up] -> 200: new row (finish-to-start-next-day, None)   e 03-23..03-24
revive g's old row beside its new one -> 400 "Revive failed for [TaskDependency with id=<id>]: Can't unretire
  the entity because a field has a non-unique value for a unique index: sgcu_task_dependencies"
```

**Teaches**

| remove by | the TaskDependency row | undo |
|---|---|---|
| `DELETE /entity/task_dependencies/<id>` | retired: 404 on `GET`, listed under `return_only: retired` | `POST .../<id>?revive=1`, same id, type and offset |
| `remove` on the downstream Task's `upstream_tasks` | erased: not listed as retired | re-create; revive is 404 |
| `remove` on the upstream Task's `downstream_tasks` | erased, the same | re-create; revive is 404 |

| the downstream Task | after the edge is removed | after revive or re-create |
|---|---|---|
| unpinned | dates held where the edge put them; no longer follows the upstream | rescheduled at once from the upstream's current dates |
| pinned, in violation | dates and `pinned` held; `dependency_violation` false | dates held; `dependency_violation` true again |

- **Delete the row, not the link.** An undo stack that removes an edge by a `multi_entity` `remove`
  cannot bring it back: the row is gone, and re-adding through `upstream_tasks` writes a new row
  typed `finish-to-start-next-day` with no offset. Record the row id and `DELETE` it.
- A re-created row with the same type and offset places the Task as the revived row would. The
  difference is the id, and the retired original then cannot be revived: the pair is unique across
  live rows, so revive after re-create is the 400 above. Undo by revive, or by re-create, not both.
- Neither route restores the downstream Task's old dates. An unpinned Task snaps to the edge as
  measured against the upstream now (probe 085); an undo that wants the old dates writes them, and the `start_date` write pins the Task
  (probe 093).
- An edge places an unpinned Task exactly, not at the earliest: l1 and l3, written late, were pulled
  back to the edge. A pinned Task placed later than that reads `dependency_violation` false for both
  types (l2, l4); only one placed earlier (d) reads true.
