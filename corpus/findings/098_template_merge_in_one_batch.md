---
tags: [task-template, batch, task, dependency]
endpoints: [POST /entity/_batch, PUT /entity/<type>/<id>, POST /entity/<type>, DELETE /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 1 template and 5 Shots made and deleted, all provisioned by the probe; 30.3s, 73 calls
verdict: Recipe 015's merge fits one `_batch`: requests run in order, so a `task_template` write sees claims made earlier in the batch, and `null` then `T` on the same Shot re-runs the apply.
---

# 098_template_merge_in_one_batch

**Q** Can recipe 015's three steps (claim Tasks by `template_task`, clear `task_template`, set it) run
as one `_batch`, with the same Tasks and edges as the split sequence?

**Endpoint** `POST /entity/_batch ; PUT /entity/shots/<id> ; POST /entity/tasks/_search ; POST /entity/task_dependencies/_search`

**Docs claim** Silent on the order a batch applies its requests and on server-side work between them.

**Actual**

```
template tt: a@step1, b@step2, dep b on a start-to-start offset_days 1

(a) bare Shot, hand-made a@step1 (ip) and b@step2
    ONE batch [claim a, claim b, Shot task_template tt] -> 200
    2 Tasks: a template_task=tt:a ip, b template_task=tt:b wtg; dep b on a start-to-start 1
(b) Shot created with tt, generated b deleted
    ONE batch [Shot task_template null, Shot task_template tt] -> 200, rows' task_template [None, <tt>]
    2 Tasks: a, b re-created (new id); dep b on a start-to-start 1
(c) Shot created with tt, generated b deleted, hand-made b@step2 (ip) added
    ONE batch [claim b, Shot null, Shot tt] -> 200
    2 Tasks: a wtg, the hand-made b template_task=tt:b ip; dep b on a start-to-start 1
control (c) setup, split: batch claim, PUT null, PUT tt -> 200, 200, 200
    2 Tasks: a wtg, the hand-made b template_task=tt:b ip; dep b on a start-to-start 1
control (b) setup, split: PUT null, PUT tt -> 200, 200
    2 Tasks: a, b re-created; dep b on a start-to-start 1
left clean: 0 Shots, 0 Tasks, 0 templates zzprobe_098_*
```

**Teaches**
- A batch applies its requests in order and each sees the one before: a claim earlier in the batch
  stops the apply from duplicating that Task, exactly as when the claim is a call of its own.
- Two updates of the same field on the same record in one batch are not collapsed. `null` then `T`
  runs the apply, as two PUTs do (probe 084, Shot D); `T` alone on a Shot that holds `T` does not.
- The one-batch merge and recipe 015's split sequence left the same Tasks, statuses and edges; the
  template's edge was written onto the claimed hand-made Task in both.
- One call instead of three, and atomic: a failing claim rolls the clear and the set back with it
  (recipe 002). Recipe 020 is this as code.
