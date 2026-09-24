---
intent: Undo a task template merge, returning an entity's Tasks, fields and dependencies to their state before it
tags: [task-template, task, dependency, destructive]
endpoints: [POST /entity/<type>/_search, GET /entity/<type>/<id>, PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>]
scope: api
measured: sandbox project written, 2 templates and 1 Shot made and deleted; 43.6 s, 104 calls
---

# 019_undo_task_template_merge

A merge (recipe 015) cannot be undone from what is left after it: the apply overwrote
`sg_sort_order`, `sg_description` and `duration` on every Task linked to the new template (probe 096),
and every other field the template sets (probe 102). Take a snapshot before the merge. The undo writes the old `template_task` on
each Task first, then the old `task_template`, then deletes what the merge made and writes the snapshot's
fields back. Entity first makes duplicates.

## Call

```python
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
SLUG = {"Shot": "shots", "Asset": "assets", "Sequence": "sequences"}
# The fields probe 096 saw the apply overwrite. Probe 102 adds content, step, est_in_mins,
# task_reviewers, milestone and custom fields, when the template sets them: add the ones yours set.
KEEP = ["template_task", "sg_sort_order", "sg_description", "duration"]


def search(slug, filters, fields):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": filters, "fields": fields, "page": {"size": 500}})
    r.raise_for_status()
    return r.json()["data"]


def link(row, field):
    return (row["relationships"].get(field) or {}).get("data")


def snapshot(entity):
    """Read before the merge: the entity's template, each Task's fields, the dependency ids."""
    sh = c.get(f"/entity/{SLUG[entity['type']]}/{entity['id']}",
               params={"fields": "task_template"}).json()["data"]
    tasks = search("tasks", [["entity", "is", entity]], KEEP)
    ids = [{"type": "Task", "id": t["id"]} for t in tasks]
    deps = search("task_dependencies", [["task", "in", ids]], ["task"]) if ids else []
    return {"task_template": link(sh, "task_template"),
            "tasks": {t["id"]: {**{k: v for k, v in t["attributes"].items() if k in KEEP},
                                "template_task": link(t, "template_task")} for t in tasks},
            "deps": {d["id"] for d in deps}}


def undo_merge(entity, snap):
    slug = SLUG[entity["type"]]
    before = snap["tasks"]
    now = search("tasks", [["entity", "is", entity]], ["template_task"])

    # 1. Tasks first. An entity write while they still point at the new template's tasks makes the
    #    old template re-create them and move its edges onto the copies (probe 096).
    for t in now:
        old = before.get(t["id"])
        if old and (link(t, "template_task") or {}).get("id") != (old["template_task"] or {}).get("id"):
            c.put(f"/entity/tasks/{t['id']}", json={"template_task": old["template_task"]}).raise_for_status()

    # 2. The old template. A non-null value re-syncs its Tasks and drops the new template's edges
    #    between them; null does nothing.
    c.put(f"/entity/{slug}/{entity['id']}", json={"task_template": snap["task_template"]}).raise_for_status()

    # 3. What the merge made. A Task delete retires its edges (probe 089).
    for t in now:
        if t["id"] not in before:
            c.delete(f"/entity/tasks/{t['id']}").raise_for_status()
    ids = [{"type": "Task", "id": i} for i in before]
    for d in search("task_dependencies", [["task", "in", ids]], ["task"]) if ids else []:
        if d["id"] not in snap["deps"]:
            c.delete(f"/entity/task_dependencies/{d['id']}").raise_for_status()

    # 4. The fields both applies overwrote.
    for i, old in before.items():
        data = {k: v for k, v in old.items() if k != "template_task"}
        c.put(f"/entity/tasks/{i}", json=data).raise_for_status()


shot = {"type": "Shot", "id": 1234}
snap = snapshot(shot)
# ... apply_template(shot, 57) from recipe 015 ...
undo_merge(shot, snap)
```

## Response

```
A: comp, roto, lay; roto on comp.  B: comp, lay, paint; lay on comp SS+1, paint on lay
before the merge   3 Tasks, 1 edge   comp ip "hand", lay order 99, roto "hand" 1440
after the merge    4 Tasks, 3 edges  comp, lay: B's order/desc/dur
step 1  PUT comp, lay template_task A.*  -> nothing else changes
step 2  PUT Shot task_template A         -> B's lay-on-comp edge removed, fields reset to A's
step 3  DELETE paint                     -> 3 Tasks, 1 edge (roto on comp)
step 4  PUT the snapshot's fields        -> "hand", 99, 1440 back; comp still ip
```

## Notes

- Step 4 is what makes it an undo rather than a reapply of A. Status survives both applies, so
  it is not in `KEEP`. Assignees and dates are only filled where empty (probe 102): add them when the
  Task had none before. `snapshot` reads `attributes` only; read `step` and
  `task_reviewers` with `link` if you add them.
- When the entity had no template before, step 2 writes null and the server does nothing. Step 3's
  dependency sweep is then the only thing that removes the new template's edges between old Tasks.
- The dependency sweep compares ids, so an edge the merge deleted is not restored. A merge deletes an
  edge between two claimed Tasks that the template lacks, or holds with another type, offset or
  direction, and erases the row (probes 101, 102): revive cannot bring it back. Snapshot each edge's
  ends, type and offset and re-create the missing ones (recipe 016).
- Events: each write logs like any other (probe 090). The undo leaves `Shotgun_Task_Change` rows
  for `template_task` behind; the history is not rewritten.
