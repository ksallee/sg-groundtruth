---
tags: [task-template, dependency, batch]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 3 Shots, 5 Tasks, 1 template made and deleted; 21.6 s, 56 calls
verdict: A template apply copies a missing edge between two Tasks whose `template_task` already match it, whether either was claimed, kept, or created by that same call.
---

# 099_template_apply_edge_copy_kept

**Q** Recipe 015's merge apply copies a template's `TaskDependency` edges onto Tasks it claims (probe
092 measured both ends claimed in the same run). Does it also copy an edge when one end was already
linked to its template task before the run and the other is newly claimed; when both ends were already
linked and only the edge is missing; and when one end is a Task the apply itself creates?

**Endpoint** `POST /entity/<type> ; PUT /entity/<type>/<id> ; POST /entity/_batch ; POST /entity/<type>/_search`

**Docs claim** Silent, as probe 092.

Every row is provisioned by the probe; no operator step.

**Actual**

```
template tt: x@stepA, y@stepB, edge y on x finish-to-start-next-day

case 1  x kept (template_task=x since create), y hand-made then claimed this run
  before                   x template_task=set  y template_task=None  edge none
  _batch claim y.template_task -> 200
  after claim, before apply  x template_task=set  y template_task=set   edge none
  PUT task_template null, then tt -> 200, 200
  after                    x template_task=set  y template_task=set   edge: y on x finish-to-start-next-day

case 2  x kept, y kept (both template_task set at create), no edge on site
  before  x template_task=set  y template_task=set    edge none
  PUT task_template null, then tt -> 200, 200 (2 Tasks on the Shot, none created)
  after   x template_task=set  y template_task=set    edge: y on x finish-to-start-next-day

case 3  x kept, no Task for y on the Shot at all
  before  x template_task=set  y not yet created       edge none
  PUT task_template null, then tt -> 200, 200 (apply creates y)
  after   x template_task=set  y template_task=set (new Task)  edge: y on x finish-to-start-next-day

left clean: Tasks zzprobe_099* site-wide 0, TaskDependency rows on the 8 Tasks seen 0,
            TaskTemplates 0, Shots 0
```

**Teaches**
- The edge is copied in all three cases: kept+claimed, kept+kept with the edge missing, and
  kept+created. Probe 092 already showed claimed+claimed, so every pairing of `{kept, claimed,
  created}` a merge apply can produce ends up holding the template's edge.
- The copy comes from the `task_template` write, not from the claim. In case 1 the `_batch` claim set
  `y.template_task` and left the pair with no edge; the edge appeared only after the PUT.
- **The apply fills edges between linked Tasks, not only the ones it just touched.** Case 2 claimed
  and created nothing: both Tasks already had `template_task` set, yet the missing edge appeared.
- Clearing and re-setting `task_template` over Tasks linked by an earlier apply fills a missing edge
  (case 2), but the same write re-syncs those Tasks' fields to the template (probe 102). It is not a
  safe way to repair edges alone.
