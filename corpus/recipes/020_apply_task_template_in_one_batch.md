---
intent: Apply a task template to an entity that already has Tasks, without duplicates, in one atomic call
tags: [task-template, batch]
endpoints: [POST /entity/<type>/_search, POST /entity/_batch]
scope: api
measured: sandbox project written, 1 template and 5 Shots made and deleted; 30.3 s, 73 calls
---

# 020_apply_task_template_in_one_batch

Recipe 015 as a single `_batch`. The requests run in order, so the `template_task` claims land before
the `task_template` write reads them, and a `null` then the template on the same entity re-runs the
apply (probe 098). Nothing lands if any request fails (recipe 002).

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
    return task["attributes"]["content"], (link(task, "step") or {}).get("id")


def apply_template(entity, template_id):
    """Claim same-name, same-step Tasks, clear, set: one atomic call. Returns the claim count."""
    tpl_ref = {"type": "TaskTemplate", "id": template_id}
    tpl = search("tasks", [["task_template", "is", tpl_ref]], ["content", "step"])
    have = search("tasks", [["entity", "is", entity]], ["content", "step", "template_task"])
    mine = {t["id"] for t in tpl}
    taken = {(link(t, "template_task") or {}).get("id") for t in have}   # one link per template task (probe 106)
    free = {key(t): t for t in have if (link(t, "template_task") or {}).get("id") not in mine}
    reqs = [{"request_type": "update", "entity": "Task", "record_id": free[key(t)]["id"],
             "data": {"template_task": {"type": "Task", "id": t["id"]}}}
            for t in tpl if key(t) in free and t["id"] not in taken]
    claimed = len(reqs)
    # The apply runs only when the value changes (probe 084); null first makes it change, always.
    for value in (None, tpl_ref):
        reqs.append({"request_type": "update", "entity": entity["type"], "record_id": entity["id"],
                     "data": {"task_template": value}})
    c.post("/entity/_batch", json={"requests": reqs}).raise_for_status()
    return claimed


apply_template({"type": "Shot", "id": 1234}, 56)
```

## Response

```
tt: a@step1, b@step2, dep b on a start-to-start offset_days 1
Shot made with tt, generated b deleted, hand-made b@step2 at ip added
batch [claim b, Shot task_template null, Shot task_template tt] -> 200
after  2 Tasks
  a  step1  template_task=<tt a>  wtg
  b  step2  template_task=<tt b>  ip     the hand-made Task, claimed, not duplicated
  TaskDependency b on a start-to-start offset_days 1
the same setup through recipe 015's three calls: the same 2 Tasks, statuses and edge
```

## Notes

- Two reads and one write, against recipe 015's two reads and up to four writes. The read of the
  entity's current `task_template` is gone: the unconditional `null` makes the set always a change.
- The server still re-syncs the claimed Tasks and resets their edges to the template's, as in recipe 015.
- The key caveat of recipe 015 stands: two Tasks with the same `content` and `step` leave one unclaimed.
- As in recipe 015, at most one Task per template task may be linked before the batch: with two, the
  apply re-syncs and wires the server's pick (probe 106).
- Keep the batch inside the size window of recipe 002 when an entity holds hundreds of Tasks.
