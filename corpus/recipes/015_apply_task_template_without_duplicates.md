---
intent: Apply a task template to an entity that already has Tasks, without duplicating the ones it already holds
tags: [task-template, task, batch, dependency]
endpoints: [POST /entity/<type>/_search, POST /entity/_batch, GET /entity/<type>/<id>, PUT /entity/<type>/<id>]
scope: api
measured: sandbox project written, 2 templates and 1 Shot made and deleted
---

# 015_apply_task_template_without_duplicates

Writing `task_template` on an entity adds one Task per template task that no Task on the entity
points at through `template_task`, and duplicates everything else (probe 084). Point each existing
Task of the same `content` and `step` at its template task first, and the server's own apply then
creates only what is missing, with the template's fields and dependencies (probe 083).

## Call

```python
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}


def search(slug, filters, fields):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": filters, "fields": fields, "page": {"size": 500}})
    r.raise_for_status()
    return r.json()["data"]


def link(row, field):
    return (row["relationships"].get(field) or {}).get("data")


def key(task):
    """What makes two Tasks the same work: their name and their pipeline step."""
    return task["attributes"]["content"], (link(task, "step") or {}).get("id")


def apply_template(entity, template_id):
    """Put a template's Tasks on an entity that may already have some, without duplicating any."""
    tpl_ref = {"type": "TaskTemplate", "id": template_id}
    slug = {"Shot": "shots", "Asset": "assets", "Sequence": "sequences"}[entity["type"]]
    tpl = search("tasks", [["task_template", "is", tpl_ref]], ["content", "step"])
    have = search("tasks", [["entity", "is", entity]], ["content", "step", "template_task"])
    mine = {t["id"] for t in tpl}

    # 1. The apply skips a template task that a Task on the entity already points at (probe 084).
    #    Point each same-name, same-step Task at its template task, so the server skips it.
    free = {key(t): t for t in have if (link(t, "template_task") or {}).get("id") not in mine}
    claim = [{"request_type": "update", "entity": "Task", "record_id": free[key(t)]["id"],
              "data": {"template_task": {"type": "Task", "id": t["id"]}}}
             for t in tpl if key(t) in free]
    if claim:
        r = c.post("/entity/_batch", json={"requests": claim})
        r.raise_for_status()

    # 2. The apply runs only when the value changes (probe 084): clear it first if it is already set.
    cur = c.get(f"/entity/{slug}/{entity['id']}", params={"fields": "task_template"}).json()["data"]
    if (link(cur, "task_template") or {}).get("id") == template_id:
        c.put(f"/entity/{slug}/{entity['id']}", json={"task_template": None}).raise_for_status()
    c.put(f"/entity/{slug}/{entity['id']}", json={"task_template": tpl_ref}).raise_for_status()
    return len(claim)


apply_template({"type": "Shot", "id": 1234}, 56)
```

## Response

```
tt1: comp@Animation, roto@Character FX
tt2: comp@Animation, roto@Comp, paint@FX, paint -> comp start-to-start offset_days 1
Shot created with tt1, plus a hand-made paint@FX at status ip
before           3 Tasks
  47295 roto   Character FX  template_task=<tt1 roto>  wtg
  47296 comp   Animation     template_task=<tt1 comp>  wtg
  47297 paint  FX            template_task=None        ip
apply_template(shot, tt2) -> 2 claimed (comp, paint)
after            4 Tasks
  47295 roto   Character FX  template_task=<tt1 roto>  wtg
  47296 comp   Animation     template_task=<tt2 comp>  wtg
  47297 paint  FX            template_task=<tt2 paint> ip   upstream [47296]
  47298 roto   Comp          template_task=<tt2 roto>  wtg   the one new Task
  TaskDependency 47297 on 47296 start-to-start offset_days 1
apply_template(shot, tt2) again -> 0 claimed, the same 4 Tasks and 1 dependency
```

## Notes

- **The server copies dependencies onto claimed Tasks too.** `paint` and `comp` both existed before
  the apply, and the apply still wrote the template's `start-to-start` edge between them. A merge by
  hand would have to copy the edges itself.
- The claim rewrites `template_task`. A Task that pointed at another template's task (`comp` above)
  now points at this template's, so the provenance of the first apply is lost.
- Nothing is removed. `roto` at the old step stays; deleting what the new template lacks is the
  caller's decision, and probe 089 lists what a Task delete unlinks.
- The key is `content` plus `step` id. Two Tasks on the entity with the same key keep only the last
  in `free`, so the other is left unclaimed and a duplicate stays.
- Set fields such as status survive the claim: `paint` kept `ip`. Only `template_task` is written.
