---
intent: Remove one dependency between two Tasks and put it back on undo, with its type and offset
tags: [task, dependency, destructive]
endpoints: [POST /entity/<type>/_search, DELETE /entity/<type>/<id>, POST /entity/<type>/<id>]
scope: api
measured: sandbox project written, 1 Shot and 5 Tasks made and deleted
---

# 0XX_remove_and_restore_a_dependency

`DELETE` on the TaskDependency row retires it, and revive brings back the same row with its
`dependency_type` and `offset_days`. A `remove` on `upstream_tasks` or `downstream_tasks` erases the
row, and nothing brings it back (probe 095).

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}


def fail(r):
    raise SystemExit(json.dumps(r.json()["errors"], indent=2))


def edge_id(downstream_id, upstream_id):
    """The row id for one edge. `task` is the downstream Task, `dependent_task` the upstream (probe 085)."""
    r = c.post("/entity/task_dependencies/_search", headers=ARR, json={
        "filters": [["task", "is", {"type": "Task", "id": downstream_id}],
                    ["dependent_task", "is", {"type": "Task", "id": upstream_id}]],
        "fields": ["dependency_type", "offset_days"]})
    if not r.ok:
        fail(r)
    rows = r.json()["data"]
    return rows[0]["id"] if rows else None


def remove_edge(row_id):
    """Retire the row. Keep the id: it is the undo."""
    r = c.delete(f"/entity/task_dependencies/{row_id}")
    if r.status_code != 204:
        fail(r)


def restore_edge(row_id):
    """Revive the same row: same id, type and offset. The downstream Task reschedules at once."""
    r = c.post(f"/entity/task_dependencies/{row_id}", params={"revive": 1})
    if not r.ok:
        fail(r)    # 400 "... non-unique value for a unique index: sgcu_task_dependencies" if the pair was re-linked
    return r.json()["meta"]["did_revive"]


row = edge_id(47339, 47337)
remove_edge(row)
print(restore_edge(row))
```

## Response

```
edge_id -> 3764   (finish-to-start-next-day, offset_days 2)
DELETE /entity/task_dependencies/3764 -> 204
  g 03-11..03-12 held; upstream moved to end 03-13; g does not follow
POST /entity/task_dependencies/3764?revive=1 -> 200 {"did_revive": true}
  row 3764 (finish-to-start-next-day, 2); g 03-18..03-19, placed from the upstream's current end
```

## Notes

- The revived edge places the Task from the upstream's current dates, not the dates it had when the
  edge was removed. An undo that wants those dates writes them after the revive, which pins the Task
  (probe 087).
- A pinned downstream Task keeps its dates through both calls. Its `dependency_violation` reads false
  while the edge is retired and true again after revive if it is still placed too early.
- If something re-linked the same pair in between, revive is a 400 on the unique index. Delete the new
  row first, or keep it and drop the undo entry.
- A `remove` through the `multi_entity` fields has no undo: re-create the row with its type and offset
  (recipe 016), which gets a new id.
