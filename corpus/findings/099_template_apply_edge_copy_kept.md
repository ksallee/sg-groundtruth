---
tags: [task-template, dependency, task, batch]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 3 Shots, 5 Tasks, 1 template made and deleted; wall time and call count unrecorded
verdict: A template apply copies a missing edge between two Tasks whose `template_task` already match it, whether either was claimed, kept, or created by that same call.
---

# 099_template_apply_edge_copy_kept

**Q** Recipe 015's merge apply copies a template's `TaskDependency` edges onto Tasks it claims (probe
092 measured both ends claimed in the same run). Does it also copy an edge when one end was already
linked to its template task before the run and the other is newly claimed; when both ends were already
linked and only the edge is missing; and when one end is a Task the apply itself creates?

**Endpoint** `POST /entity/<type> ; PUT /entity/<type>/<id> ; POST /entity/_batch ; POST /entity/<type>/_search`

**Docs claim** Silent, as probe 092.

**Actual**

```
template tt: x@stepA, y@stepB, edge y on x finish-to-start-next-day

case 1  x kept (template_task=x since create), y hand-made then claimed this run
  before  x template_task=set  y template_task=None   edge none
  _batch claim y.template_task -> 200
  PUT task_template null, then tt -> 200, 200
  after   x template_task=set  y template_task=set    edge: y on x finish-to-start-next-day

case 2  x kept, y kept (both template_task set at create), no edge on site
  before  x template_task=set  y template_task=set    edge none
  PUT task_template null, then tt -> 200, 200 (nothing claimed, both already matched)
  after   x template_task=set  y template_task=set    edge: y on x finish-to-start-next-day

case 3  x kept, no Task for y on the Shot at all
  before  x template_task=set  y not yet created       edge none
  PUT task_template null, then tt -> 200, 200 (apply creates y)
  after   x template_task=set  y template_task=set (new Task)  edge: y on x finish-to-start-next-day
```

**Teaches**
- The edge is copied in all three cases: kept+claimed, kept+kept with the edge missing, and
  kept+created. Probe 092 already showed claimed+claimed, so every pairing of `{kept, claimed,
  created}` a merge apply can produce ends up holding the template's edge.
- **The apply reconciles edges structurally, not by what it just touched.** Case 2 claimed nothing:
  both Tasks already had `template_task` set, yet the missing edge still appeared. Writing
  `task_template` compares the template's dependency graph against `template_task` links on the
  entity's Tasks every time, not just against Tasks the call itself created or claimed.
- A caller re-running recipe 015 against Tasks that already hold links from an earlier apply gets the
  edges filled in for free: clearing and re-setting `task_template` is enough, with no need to re-walk
  the template's dependency list by hand.
- Probe 092's reschedule finding generalizes with it: whichever of these three routes produces the
  edge, an unpinned downstream Task with dates already set moves to satisfy it the moment the edge
  exists.
