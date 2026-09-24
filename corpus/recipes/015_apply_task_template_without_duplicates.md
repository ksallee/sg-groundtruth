---
intent: Apply a task template to an entity that already has Tasks, without duplicating the ones it already holds
tags: [task-template, task, batch, dependency]
endpoints: [POST /entity/<type>/_search, POST /entity/_batch, GET /entity/<type>/<id>, PUT /entity/<type>/<id>]
scope: api
measured: sandbox project written, 2 templates and 1 Shot made and deleted; re-run 2026-09-24, 2 Shots
---

# 015_apply_task_template_without_duplicates

Writing `task_template` T on an entity creates one Task per template task that no Task on the entity
points at through `template_task`, so a hand-made Task of the same `content` and `step` is duplicated
(probe 084). Point each such Task at its template task first, and the apply creates only the Tasks
still missing, with the template's fields and dependencies (probe 083). It does not leave the claimed
Tasks alone: every Task linked to T is re-synced to T, fields and edges (probes 096, 102). Snapshot what
a person set before the apply and write it back after (recipe 019).

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
    #    Never claim a template task another Task already points at: with two linked, the apply
    #    re-syncs and wires one of them, picked unpredictably (probe 106).
    taken = {(link(t, "template_task") or {}).get("id") for t in have}
    free = {key(t): t for t in have if (link(t, "template_task") or {}).get("id") not in mine}
    claim = [{"request_type": "update", "entity": "Task", "record_id": free[key(t)]["id"],
              "data": {"template_task": {"type": "Task", "id": t["id"]}}}
             for t in tpl if key(t) in free and t["id"] not in taken]
    if claim:
        r = c.post("/entity/_batch", json={"requests": claim})
        r.raise_for_status()

    # 2. The apply runs only when the value changes (probe 084): clear it first if it is already set.
    #    The set re-syncs every Task linked to the template, hand edits included (probe 102).
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
tt: a@step1, b@step2, dep b on a start-to-start offset_days 1 (re-run, the claim skip of probe 106)
Shot with a, a both linked to <tt a>, a unlinked, b unlinked
apply_template(shot, tt) -> 1 claimed (b); the unlinked a is skipped, <tt a> stays linked twice, no new Task
Shot with a, b unlinked: apply_template(shot, tt) -> 2 claimed, no new Task, 1 dependency
```

## Notes

- **The claim writes only `template_task`; the entity write then overwrites** every Task linked to T,
  claimed or not (probe 102):

  | field | after step 2 |
  |---|---|
  | `content`, `step`, `est_in_mins`, `sg_description`, `sg_sort_order`, `task_reviewers`, `milestone`, a custom field (one list and one checkbox field probed on one site) | T's value, where T sets one |
  | `task_assignees`, `start_date`, `due_date` | kept; filled from T only when empty |
  | `duration` | T's on a Task without dates; kept on a dated one; on a Task with only one date, kept null (probe 108) |
  | `sg_status_list` | kept (`paint` kept `ip`) |
  | a numeric 0 on T (`est_in_mins`; `duration` on a Task without dates) | 0: it overwrites (probe 108) |
  | any field T leaves empty: null, a checkbox's false, a text `""` (stored as null) | kept (probe 108) |

  Tasks linked by an earlier apply of T are re-synced too: re-running step 2 wipes their hand edits.
- **The apply resets the edges between Tasks linked to T to T's.** Every pairing of claimed, kept and
  created ends gets T's missing edges (probes 092, 099): `paint` and `comp` both existed before the
  apply and still got the `start-to-start` edge.

  | the pair already holds | the apply |
  |---|---|
  | no edge, T has one | creates T's |
  | the edge in T's direction with another type or offset, or the reverse edge | deletes it and creates T's, a new id; the old row is erased, not retired (probes 101, 102) |
  | T's edge with `offset_days` null where T holds 0, or 0 where T holds null | the same: erased, re-created with T's value (probe 105) |
  | an edge T lacks, both ends linked to T | deletes it (probe 102) |
  | an edge T lacks, a Task linked to T depending on a Task not linked to T (unlinked, another template, another entity) | **erases it** (probes 107, 109) |
  | an edge T lacks, a Task not linked to T depending on one linked to T | keeps it (probes 101, 102, 109) |

  The PUT is 200 in every case. Read each linked Task's `upstream_tasks` before the apply and
  re-create the outside edges to keep; write `offset_days` on an entity edge exactly as T holds it,
  null or 0, to keep its id.
- **A copied edge reschedules.** The server moves an unpinned downstream Task to satisfy an edge it
  copied; a pinned one keeps its dates and flags `dependency_violation` (probe 092). Pin the Tasks
  whose dates must hold before step 2.
- The claim rewrites `template_task`. A Task that pointed at another template's task (`comp` above)
  now points at this template's, so the provenance of the first apply is lost.
- No Task is removed. `roto` at the old step stays; deleting what the new template lacks is the
  caller's decision, and probe 089 lists what a Task delete unlinks.
- The key is `content` plus `step` id. Two Tasks on the entity with the same key keep only the last
  in `free`, so the other is left unclaimed and a duplicate stays.
- **Before an apply, at most one Task per template task may be linked to it.** With two, the apply
  re-syncs and wires one, the server's pick, not predictable by id, age, name or edges. The other keeps
  its fields and link; its edges of T's shape were deleted or kept unevenly (probe 106). Unlink the others (`template_task` null) first; `taken` above keeps the
  claim from making a second link.
- The claims, the clear and the set fit one `_batch`, in that order, with the same result: recipe 020
  (probe 098). Undo is recipe 019 (probe 096).
