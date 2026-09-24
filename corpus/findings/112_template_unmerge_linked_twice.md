---
tags: [task-template, batch, dependency, trap]
endpoints: [POST /entity/_batch, POST /entity/<type>, POST /entity/<type>/_search, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2 templates, 4 Shots, 19 Tasks per run; 7 runs; committed probe 37.3-38.7 s, 80 calls
verdict: Undo relinking two Tasks to one template task: A wires either one (11 of 14 picked the loser), nothing is made. Relink the loser after the task_template write: then it matches the one-link undo.
---

# 112_template_unmerge_linked_twice

**Q** Before a merge, two Tasks on one Shot both point `template_task` at template A's task x. The
merge into B unlinks the loser and claims the winner for B.x. The undo (recipe 022's order) writes both
old links back, then the Shot's `task_template` A. Which Task does A's apply re-sync and wire, is the
pick stable, is anything created, and does the end state equal the pre-merge state?

**Endpoint** `POST /entity/_batch ; POST /entity/tasks ; POST /entity/tasks/_search ; POST /entity/task_dependencies/_search ; DELETE /entity/<type>/<id>`

**Docs claim** Silent.

Every precondition is provisioned by the probe (both templates, the Shots, the Tasks); no operator step.

**Actual**

```
A: w, x, y; x on w, y on x.  B: x (same content, step), z; z on x.  Fields differ between A and B.
D1, D2, D3 made with A (w, xa, y, 2 edges), xa "hand-a" order 55; xb POSTed with template_task A.x,
  content x_hand, "hand-b", 99, 1440, no edge.  Control C: the same without xb.
merge, batch [xb null, xa B.x, Shot null, Shot B] -> 200: + z, z on xa; xa on w erased (probe 109)
undo batch 1 [xa A.x, xb A.x, Shot A, DELETE z] -> 200 (D3: xb A.x moved after Shot A)
  Task count 4, same ids, nothing created, every Shot, every run
  xb wired:  xb content=x order 20 desc A.x dur 480 | xa keeps B's 120 B.x 960, no edge
             xb on w, y on xb new; y on xa (kept by the merge) deleted
  xa wired:  xa A's fields, xa on w new, y on xa same id | xb keeps x_hand 99 hand-b 1440
wired after batch 1, D1 D2, runs 1-7 (1-4 a draft without D3): xb xb | xa xb | xb xa | xb xa | xb xb | xb xb | xb xb
  D3 (xb linked after Shot A), runs 5-7: xa xa xa; xb's fields unchanged
undo batch 2, the snapshot's content, order, desc, dur on every old Task -> 200
after vs before the merge (Task ids, template_task, status, fields, edges with ids)
  Tasks, links, fields: identical on every Shot, every run
  edges, xb wired:  -xa on w #a, -y on xa #b, +xb on w #new, +y on xb #new
  edges, xa wired, D3, C:  -xa on w #a, +xa on w #new     y on xa same id
  negative control, C merged vs C before: differs in template, tasks, edges
left clean every run: 0 Shots, 0 Tasks (Shot and template), 0 TaskDependency, 0 templates zzprobe_112_*
```

**Teaches**
- **Recipe 022 on this state does not undo.** A's apply re-syncs and wires one of the two Tasks,
  the server's pick (probe 106): 11 of 14 went to the loser, the Task that held no edge and was
  unlinked by the merge, and the pick flipped between identical Shots in one run. Nothing is created.
- When the loser is picked, the winner keeps B's fields and loses its edges: both of A's edges now
  sit on the loser, with new ids. Writing the snapshot's fields back does not move them. Recipe 022's
  `KEEP` lacks `content`, which A's re-sync renames on the loser: keep it.
- Relink only one Task per template task before the `task_template` write, the one that held the
  edges, and the others after it in the same batch: a `template_task` write alone changes nothing
  (probe 096). D3 did so 3 of 3 and ended as the one-link control did.
- Even the control is not the pre-merge state to the id: B's apply erased `xa on w`, a claimed Task
  on a Task outside B (probe 109), and A's apply recreates it with a new id. Every other id is kept.
