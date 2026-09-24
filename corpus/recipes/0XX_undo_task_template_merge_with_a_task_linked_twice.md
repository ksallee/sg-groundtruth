---
intent: Undo a task template merge when two Tasks pointed at the same old template task, without the server picking which one gets the edges
tags: [task-template, batch, dependency, trap]
endpoints: [POST /entity/<type>/_search, POST /entity/_batch]
scope: api
measured: sandbox project written, probe 112: reordered batch 3 runs, plain batch 7 runs; 37-39 s, 80 calls
---

# 0XX_undo_task_template_merge_with_a_task_linked_twice

Recipe 022 writes every old `template_task` before the old `task_template`. When the snapshot has two
Tasks on the same template task (the site allows it), the apply that follows re-syncs and wires only
one, the server's pick, and 11 of 14 times it was the Task that held no edge (probe 112). Relink one
Task per template task before the entity write, the one that held the edges, and the rest after it,
in the same batch. A `template_task` write on its own changes nothing else (probe 096).

## Call

```python
# snapshot() from recipe 019 before the merge, with "content" in KEEP (the apply renames the Task it
# re-syncs), plus the Task ids its edges touch:
#   snap["edged"] = {i for d in deps for i in (link(d, "task")["id"], link(d, "dependent_task")["id"])}
# Recipe 022's undo_merge builds `reqs`; replace its step 1 and step 2 with:


def claims_around_entity_write(entity, snap, now):
    """Step 1 and 2 of recipe 022, with a second link to one template task deferred past step 2."""
    before, first, late, seen = snap["tasks"], [], [], set()
    # the Task that held edges goes first, then the lowest id
    order = sorted(now, key=lambda t: (t["id"] not in snap["edged"], t["id"]))
    for t in order:
        old = before.get(t["id"])
        if not old:
            continue
        target = (old["template_task"] or {}).get("id")
        dup = target is not None and target in seen
        seen.add(target)
        if (link(t, "template_task") or {}).get("id") != target:
            (late if dup else first).append(upd("Task", t["id"], {"template_task": old["template_task"]}))
    return first + [upd(entity["type"], entity["id"], {"task_template": snap["task_template"]})] + late
```

## Response

```
A: w, x, y; x on w, y on x.  xa (edges) and xb (none) both on A.x.  Merged into B: xa B.x, xb null
batch [xa A.x, Shot A, xb A.x, DELETE z] -> 200, 3 of 3
  xa re-synced, xa on w, y on xa; xb unchanged, linked to A.x, no edge; 4 Tasks, none made
the same with xb before Shot A: xb wired in 11 of 14, xa left with B's fields and no edge
then the snapshot's fields -> Tasks, links and fields equal the pre-merge read
```

## Notes

- The end state equals the one-link undo, which is not the pre-merge state to the id: an edge the
  merge erased, a claimed Task on a Task outside the new template (probe 109), comes back new.
- Only the case of one Task that held A's edges and one that held none was measured. Two Tasks that
  both held edges: not measured.
- The deferred link leaves the second Task pointing at the template task, so a later apply of A meets
  the same pick (probe 106). Leave it null instead if nothing reads the link.
