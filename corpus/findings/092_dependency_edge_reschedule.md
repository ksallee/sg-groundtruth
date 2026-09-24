---
tags: [dependency, task, date, task-template]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 1 Shot, 6 Tasks, 1 template made and deleted by the probe; 22.4 s, 49 calls
verdict: A new edge reschedules an unpinned downstream Task at once, whether POSTed or copied by a template apply on claim. A pinned one keeps its dates and flags `dependency_violation`.
---

# 092_dependency_edge_reschedule

**Q** Does adding a TaskDependency edge reschedule an unpinned downstream Task that now violates it, or
does only a date write (probe 087)? Both for a direct create and for the edge the server copies on a
claimed Task during a template apply (recipe 015).

**Endpoint** `POST /entity/task_dependencies ; POST /entity/_batch ; PUT /entity/shots/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent on scheduling, and on what a template apply does to Tasks that already exist.

**Actual**

```
every Task created 2026-03-02..03-03 (Mon..Tue), dur 960; one per case set pinned=true first
(a) POST /entity/task_dependencies {task: dn|pn, dependent_task: up, finish-to-start-next-day} -> 201, 201
  before  up 03-02..03-03  dn 03-02..03-03 pinned=False violation=False  pn 03-02..03-03 pinned=True violation=False
  after   up 03-02..03-03  dn 03-04..03-05 pinned=False violation=False  pn 03-02..03-03 pinned=True violation=True

(b) template a, b, c undated; edges b on a, c on a, finish-to-start-next-day
    Shot holds hand-made a, b, c with no edges; c pinned
  _batch update template_task on a, b, c -> 200     dates, pinned and violation unchanged
  PUT Shot task_template null -> 200; PUT Shot task_template tt -> 200; still 6 Tasks, none generated
  TaskDependency b on a finish-to-start-next-day offset_days=None     (copied)
  TaskDependency c on a finish-to-start-next-day offset_days=None     (copied)
  before  a 03-02..03-03  b 03-02..03-03 pinned=False violation=False  c 03-02..03-03 pinned=True violation=False
  after   a 03-02..03-03  b 03-04..03-05 pinned=False violation=False  c 03-02..03-03 pinned=True violation=True
  3 s later: the same
```

**Teaches**
- **An edge is a scheduling write.** Creating one moves an unpinned downstream Task to satisfy it, the
  same as the upstream date write of probe 087, `duration` held. The upstream Task does not move.
- **A template apply reschedules Tasks it did not create.** The edge it copies between claimed Tasks
  (recipe 015) moved `b` two days although no date was sent. Pin a Task whose dates a person chose
  before the apply, or restore its dates after.
- A pinned downstream Task keeps its dates and reads `dependency_violation` true from the moment the
  edge exists. Neither route sets or clears `pinned`.
- The claim itself (`template_task` written) moves nothing, and the reschedule is done before the
  `PUT` returns: a read 3 s later matched the first. The template's undated tasks copied no dates.
