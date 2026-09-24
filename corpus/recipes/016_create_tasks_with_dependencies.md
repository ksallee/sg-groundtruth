---
intent: Create a set of Tasks and the dependencies between them, with types and offsets, in two calls
tags: [task, batch, dependency, create]
endpoints: [POST /entity/_batch]
scope: api
measured: sandbox project written, 1 Shot and 4 Tasks made and deleted
---

# 016_create_tasks_with_dependencies

One `_batch` cannot link rows it creates (recipe 002), so the Tasks go in the first call and the
TaskDependency rows in the second. Writing the edges as rows is the one route that takes a
`dependency_type` and an `offset_days` and reschedules the dependents; `upstream_tasks` in a create
body links without moving any date (probe 086).

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
PROJECT_ID = 1234


def batch(requests_):
    r = c.post("/entity/_batch", json={"requests": requests_})
    if not r.ok:
        raise SystemExit(json.dumps(r.json()["errors"], indent=2))   # nothing was applied
    return r.json()["data"]


def create_tasks(entity, tasks, edges):
    """tasks: {name: fields}. edges: [(downstream, upstream, dependency_type, offset_days)]."""
    project = {"type": "Project", "id": PROJECT_ID}
    names = list(tasks)
    # 1. The Tasks. A batch cannot name a row it creates (recipe 002), so the links wait for call 2.
    rows = batch([{"request_type": "create", "entity": "Task",
                   "data": {"project": project, "entity": entity, "content": n, **tasks[n]}}
                  for n in names])
    ids = {n: row["data"]["id"] for n, row in zip(names, rows)}
    # 2. The edges, as TaskDependency rows: the one route that takes a type and an offset and
    #    reschedules the dependents (probe 086). `task` is downstream, `dependent_task` upstream.
    batch([{"request_type": "create", "entity": "TaskDependency",
            "data": {"task": {"type": "Task", "id": ids[down]},
                     "dependent_task": {"type": "Task", "id": ids[up]},
                     "dependency_type": typ, "offset_days": offset}}
           for down, up, typ, offset in edges])
    return ids


create_tasks({"type": "Shot", "id": 5678}, {
    "layout": {"start_date": "2026-03-02", "due_date": "2026-03-03"},
    "anim":   {"duration": 2400},
    "light":  {"duration": 960},
    "comp":   {"duration": 960},
}, [("anim", "layout", "finish-to-start-next-day", None),
    ("light", "anim", "start-to-start", 2),
    ("comp", "light", "finish-to-start-next-day", None)])
```

## Response

```
call 1 -> 200, 4 create rows    {'layout': 47299, 'anim': 47300, 'light': 47301, 'comp': 47302}
call 2 -> 200, 3 create rows
read back
  layout  2026-03-02..2026-03-03  duration 960
  anim    2026-03-04..2026-03-10  duration 2400  upstream [layout]   finish-to-start-next-day
  light   2026-03-06..2026-03-09  duration 960   upstream [anim]     start-to-start, offset_days 2
  comp    2026-03-10..2026-03-11  duration 960   upstream [light]    finish-to-start-next-day
```

## Notes

- A Task sent with only `duration` gets its dates from its dependency in call 2: `anim` started the
  working day after `layout` ended and ran its 2400 minutes, five 8-hour days on the probed site.
- `offset_days` is working days: `light` starts two working days after `anim` starts (probe 085).
- The four `dependency_type` values, and the error that lists them, are in probe 085. Omitting the
  type stores `finish-to-start-next-day`.
- A loop or a repeated pair in call 2 is a 400 and rolls the whole call back; the Tasks from call 1
  stay. Delete them, or resend call 2 fixed.
- Keep each call under about 200 requests (recipe 002, size note).
