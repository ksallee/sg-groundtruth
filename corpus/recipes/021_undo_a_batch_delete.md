---
intent: Delete Tasks or dependencies in one batch and undo it by reviving the same rows
tags: [batch, task, dependency, destructive]
endpoints: [POST /entity/_batch, POST /entity/<type>/<id>, POST /entity/<type>/_search]
scope: api
measured: sandbox project written, 1 Shot, 3 Tasks, 2 edges and 1 Version made and deleted; 31.0 s, 97 calls
---

# 021_undo_a_batch_delete

A `delete` inside `_batch` retires the row as `DELETE` does. Keep the ids the batch answers with:
revive each one to undo, and it comes back with the same id, fields and links (probe 103).

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
SLUG = {"Task": "tasks", "TaskDependency": "task_dependencies"}


def fail(r):
    raise SystemExit(json.dumps(r.json()["errors"], indent=2))


def delete_batch(rows):
    """rows: [(entity, id)]. One atomic call. Returns the undo entry: [(entity, id)] as deleted."""
    r = c.post("/entity/_batch", json={"requests": [
        {"request_type": "delete", "entity": e, "record_id": i} for e, i in rows]})
    if not r.ok:
        fail(r)                                  # nothing was deleted (recipe 002)
    return [(d["type"], d["id"]) for d in r.json()["data"] if d["did_delete"]]


def undo(entry):
    """Revive in reverse. A Task revives its own edges; an edge already live is skipped."""
    for entity, i in reversed(entry):
        slug = SLUG[entity]
        r = c.post(f"/entity/{slug}/_search", headers=ARR, json={
            "filters": [["id", "is", i]], "fields": ["id"], "options": {"return_only": "retired"}})
        if not r.ok:
            fail(r)
        if not r.json()["data"]:
            continue                             # live again, or erased: nothing to revive
        r = c.post(f"/entity/{slug}/{i}", params={"revive": 1})
        if not r.ok:
            fail(r)


entry = delete_batch([("TaskDependency", 4299), ("Task", 48066)])
undo(entry)
```

## Response

```
_batch delete Task 48066 -> 200
  [{"request_type": "delete", "type": "Task", "id": 48066, "uuid": "...", "did_delete": true}]
  GET 404; _search return_only retired -> [48066]; its edge 4296 retired; Version.sg_task null
POST /entity/tasks/48066?revive=1 -> 200 {"did_revive": true}
  same id and fields; edge 4296 live; Version.sg_task = 48066
_batch delete TaskDependency 4299 -> 200, did_delete true
POST /entity/task_dependencies/4299?revive=1 -> 200 {"did_revive": true}
  start-to-start, offset_days 2, same id
```

## Notes

- `_batch` takes no revive request (`request_type must be one of: create, update, delete`, recipe 002),
  so the undo is one call per row.
- Measured one row per batch. A Task and its own edge in the same batch was not measured; the check
  for an already live row in `undo` covers the edge coming back with its Task (probe 089).
- A revived Task or edge is rescheduled from the upstream's current dates (probes 089, 095).
- If the same pair was re-linked in between, the edge's revive is 400 on `sgcu_task_dependencies`
  (recipe 018).
