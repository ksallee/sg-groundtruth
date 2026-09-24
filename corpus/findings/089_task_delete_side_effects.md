---
tags: [dependency, task, published-file, version, destructive]
endpoints: [DELETE /entity/<type>/<id>, POST /entity/<type>/<id>, GET /entity/<type>/<id>, POST /entity/<type>/_search, PUT /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 3 Tasks, a Version and a PublishedFile made and deleted
verdict: Deleting a Task retires its TaskDependency rows, unlinks both neighbours without bridging them, and nulls `Version.sg_task` and `PublishedFile.task`. Revive restores all of it.
---

# 089_task_delete_side_effects

**Q** What does deleting a Task in the middle of a dependency chain do to its dependencies, its
neighbours' dates, and the Version and PublishedFile that point at it? Does revive put them back?

**Endpoint** `DELETE /entity/tasks/<id> ; POST /entity/tasks/<id>?revive=1 ; GET /entity/<type>/<id> ; POST /entity/published_files/_search`

**Docs claim** Silent on side effects. The 204 has no body.

**Actual**

```
a -FS-> b -FS-> c; Version.sg_task = b; PublishedFile.task = b
before     a 03-02..03-03 down=[b]   b 03-04..03-05 up=[a] down=[c]   c 03-06..03-09 up=[b]
DELETE /entity/tasks/b -> 204, 0 bytes
after      a 03-02..03-03 down=[]    b 404                            c 03-06..03-09 up=[]
           both TaskDependency rows: GET 404; _search with options return_only=retired: both
           Version 200 sg_task=null   PublishedFile 200 task=null   _search ["task", "is", b]: 0
PUT a due_date 03-10 -> 200          a 03-02..03-10   c 03-06..03-09 (no longer follows)
POST /entity/tasks/b?revive=1 -> 200 {"did_revive": true}
after      a 03-02..03-10 down=[b]   b 03-11..03-12 up=[a] down=[c]   c 03-13..03-16 up=[b]
           both TaskDependency rows: GET 200
           Version sg_task=b   PublishedFile task=b   _search ["task", "is", b]: 1
```

**Teaches**

| linked to the deleted Task | after `DELETE` | after revive |
|---|---|---|
| its TaskDependency rows | retired: 404 on `GET`, listed under `return_only: retired` | live again |
| the upstream and downstream neighbours | unlinked from it; **not linked to each other** | relinked |
| the neighbours' dates | unchanged | the chain rescheduled from the upstream's current dates |
| `Version.sg_task` | `null`; the Version stays | the Task again |
| `PublishedFile.task` | `null`; the file stays | the Task again |

- **A PublishedFile loses its Task and nothing says so.** The file stays live with `task` null, so a
  `["task", "is", ...]` query stops finding it and the publish reads as an orphan. Read what points
  at a Task before deleting it; the 204 names nothing.
- **The chain is cut, not bridged.** `c` stopped following `a`: moving `a` afterwards left `c` where it
  was. A sync that removes a middle Task must write the `a -> c` dependency itself if it wants one.
- Revive is a full undo on the links measured here: dependencies, `sg_task` and `task` all returned
  with the same row ids. The revived chain is rescheduled at once, so its dates are not the ones it was
  deleted with.
- A `delete` request inside `_batch` does the same to the Task, its dependency rows, its neighbours
  and `Version.sg_task`, and revive undoes it the same way (probe 103). `PublishedFile.task` was not
  measured on that route.
- Deleting a Task retires only the Task and its dependency rows, unlike deleting a Shot, which retires
  its Versions (probe 060).
