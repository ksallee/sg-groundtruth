---
intent: Undo a task template merge in one atomic call, returning Tasks, fields and dependencies to their state before it
tags: [task-template, batch, task, dependency, destructive]
endpoints: [POST /entity/<type>/_search, GET /entity/<type>/<id>, POST /entity/_batch]
scope: api
measured: sandbox project written, 2 templates and 4 Shots made and deleted; 42.0 s, 93 calls
---

# 022_undo_task_template_merge_in_one_batch

Recipe 019 as a single `_batch`. The requests run in order, so the old `template_task` claims land
before the old `task_template` write, and that write re-syncs the Tasks and removes the merge's edges
between them, as the separate call does (probe 104). Every id is read before the batch, so the batch
must leave out the edges its own `task_template` write removes: a DELETE of one of them 404s and
nothing lands. Take the snapshot of recipe 019 before the merge.

## Call

```python
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
# The fields probes 096 and 104 measured. Probe 102 adds content, step, est_in_mins, task_reviewers,
# milestone and custom fields, when the template sets them: add the ones yours set.
KEEP = ["sg_sort_order", "sg_description", "duration"]


def search(slug, filters, fields):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": filters, "fields": fields, "page": {"size": 500}})
    r.raise_for_status()
    return r.json()["data"]


def link(row, field):
    return (row["relationships"].get(field) or {}).get("data")


def upd(entity, rid, data):
    return {"request_type": "update", "entity": entity, "record_id": rid, "data": data}


def dele(entity, rid):
    return {"request_type": "delete", "entity": entity, "record_id": rid}


# snapshot(entity) is recipe 019's, taken before the merge.

def undo_merge(entity, snap):
    before = snap["tasks"]
    now = search("tasks", [["entity", "is", entity]], ["template_task"])
    ids = [{"type": "Task", "id": t["id"]} for t in now]
    deps = search("task_dependencies", [["task", "in", ids]], ["task", "dependent_task"]) if ids else []
    reqs = []

    # 1. Tasks first: the old template_task on each claimed Task.
    for t in now:
        old = before.get(t["id"])
        if old and (link(t, "template_task") or {}).get("id") != (old["template_task"] or {}).get("id"):
            reqs.append(upd("Task", t["id"], {"template_task": old["template_task"]}))

    # 2. The old template. Non-null: re-syncs its Tasks, drops the merge's edges between them. Null: nothing.
    reqs.append(upd(entity["type"], entity["id"], {"task_template": snap["task_template"]}))

    # 3. What the merge made. A Task delete retires its edges; an edge between two old Tasks that both
    #    return to a template task is already gone after step 2, and deleting it 404s the batch.
    for t in now:
        if t["id"] not in before:
            reqs.append(dele("Task", t["id"]))
    for d in deps:
        down, up = link(d, "task")["id"], link(d, "dependent_task")["id"]
        if d["id"] in snap["deps"] or down not in before or up not in before:
            continue
        removed = snap["task_template"] and before[down]["template_task"] and before[up]["template_task"]
        if not removed:
            reqs.append(dele("TaskDependency", d["id"]))

    # 4. The fields both applies overwrote.
    for i, old in before.items():
        reqs.append(upd("Task", i, {k: old[k] for k in KEEP}))

    c.post("/entity/_batch", json={"requests": reqs}).raise_for_status()


shot = {"type": "Shot", "id": 1234}
# snap = snapshot(shot); apply_template(shot, 57) from recipe 020; later:
undo_merge(shot, snap)
```

## Response

```
A: comp, roto, lay; roto on comp.  B: comp, lay, paint; lay on comp SS+1, paint on lay
Shot made with A, comp ip "hand", lay 99, roto "hand" 1440; merged into B: + paint, 3 edges
batch [claim comp, lay back to A, Shot task_template A, DELETE paint, 3 field writes] -> 200
  3 Tasks, same ids; comp ip "hand", lay 99, roto "hand" 1440; roto on comp, same edge id
  identical to the twin Shot undone by recipe 019's separate calls
the same batch plus DELETE TaskDependency lay-on-comp
  -> 404 Entity of type [TaskDependency] with id=4409 does not exist.  nothing landed
Shot with no template before: batch [claims null, Shot null, DELETE paint,
  DELETE TaskDependency lay-on-comp, 2 field writes] -> 200, identical to its twin and its snapshot
```

## Notes

- The dependency read happens before the batch, after the merge; recipe 019 reads after step 2 and
  so never meets the 404. An edge with one end back on a template task and the other on none was
  not measured: test it before relying on the rule for it.
- `snapshot` stores `template_task` per Task and `task_template` from recipe 019, keyed by Task id.
- Atomic: any failing request rolls back the claims and the template write too (recipe 002), so a
  rejected batch leaves the merged state, not a half undo. Re-read before a retry.
- The recipe 019 caveats stand: an edge the merge deleted is not restored, and the history of
  `template_task` writes stays in the event log (probe 090).
