---
tags: [batch, task, dependency, destructive]
endpoints: [POST /entity/_batch, DELETE /entity/<type>/<id>, POST /entity/<type>/<id>, GET /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 1 Shot, 3 Tasks, 2 edges, 1 Version made and deleted; 31.0 s wall, 97 calls; no operator step
verdict: A `delete` inside `_batch` retires a Task or TaskDependency exactly as `DELETE` does: same retired read-back, and revive returns the same id, fields, edges and `Version.sg_task`.
---

# 103_batch_delete_revive

**Q** Does a `delete` request inside `POST /entity/_batch` retire the row the way
`DELETE /entity/<type>/<id>` does, so that revive brings it back with the same id, fields and links?
Measured for a Task and for a TaskDependency.

**Endpoint** `POST /entity/_batch ; DELETE /entity/<type>/<id> ; POST /entity/<type>/<id>?revive=1 ; GET /entity/<type>/<id>?options[return_only]=retired ; POST /entity/<type>/_search`

**Docs claim** Silent on whether a batch delete retires. Recipe 002 measured only that `GET` 404s after it.

**Actual**

```
a, b, c; edge b on a (default type); edge c on a start-to-start +2; Version.sg_task = b
Each row goes through the batch delete, then revive, then DELETE (the control), then revive.
Task b                          _batch delete                   DELETE (control)
  response                      200 {"request_type": "delete",   204, 0 bytes
                                "type": "Task", "id": b,
                                "uuid": "...", "did_delete": true}
  GET b                         404                             404
  retired: _search, GET         [b], 200                        [b], 200
  edge b on a                   GET 404, listed retired         GET 404, listed retired
  a.downstream_tasks            [c]                             [c]
  Version.sg_task               null                            null
  revive b                      200 {"did_revive": true}        200 {"did_revive": true}
  after revive                  same id; content, dates, description, status, entity, project,
                                upstream_tasks equal to before; edge b on a live, same fields;
                                a.downstream_tasks [b, c]; Version.sg_task = b     (both routes)
TaskDependency c on a
  response                      200 {..., "type": "TaskDependency", "did_delete": true}   204
  GET row                       404                             404
  retired: _search, GET         [row], 200                      [row], 200
  c.upstream_tasks              []                              []
  revive row                    200 {"did_revive": true}        200 {"did_revive": true}
  after revive                  same id, start-to-start, offset_days 2, c.upstream_tasks [a]  (both)
negative control: a live row in the same retired reads -> _search omits it, GET options 404, every time
left clean: 0 Tasks, Shots, Versions zzprobe_103_*, 0 TaskDependency rows on a, b, c
```

**Teaches**
- **A batch `delete` is a retire, not an erase.** Every read-back matched the plain `DELETE`: the row
  lists under `return_only: retired` by `_search` and by `GET options[return_only]=retired`, and
  `POST /entity/<type>/<id>?revive=1` answers `did_revive: true`.
- The side effects of deleting a Task (probe 089) are the same on both routes: its edges retire with
  it, the neighbour's link drops, `Version.sg_task` reads null, and revive restores all of it with the
  same ids.
- An undo stack can record the ids a batch delete returns (`data[i].id`) and revive them one by one;
  recipe 018 applies to a batch-deleted edge unchanged.
- Not measured: revive inside `_batch` (it accepts only `create`, `update`, `delete`, recipe 002), a
  Task and its edge deleted in the same batch, and a PublishedFile link.

The probe provisions every row it reads; no operator step. It runs each row through the batch delete
first and the `DELETE` control second, on the same row, with a full read-back between steps.
