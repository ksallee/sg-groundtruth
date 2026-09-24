---
tags: [task-template, dependency, destructive]
endpoints: [PUT /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>, POST /entity/<type>/_search, GET /entity/<type>/<id>, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 1 template, 2 Shots, 6 Tasks, 4 edges made and deleted; 26.8 s, 72 calls
verdict: On a claimed pair, a template apply replaces an existing edge of another type, or the reverse edge, with the template's edge: the old row is erased, not retired, and the PUT is a plain 200.
---

# 101_template_edge_conflict

**Q** In a merge apply (recipe 015) the server copies template edges onto claimed Tasks. When the pair
already holds (a) an edge of another `dependency_type` in the same direction, or (b) the reverse edge,
does the apply fail and roll back, skip the edge, replace it, or add a second one?

**Endpoint** `POST /entity/_batch ; PUT /entity/shots/<id> ; POST /entity/task_dependencies/_search ; GET /entity/task_dependencies/<id>`

**Docs claim** Silent. A direct create of either edge is a 400 (probe 085).

**Actual**

```
template a, b, c; edge b on a finish-to-start-next-day. One Shot per case holds hand-made a, b, x
(no c); x on a finish-to-start-next-day is a control edge to an unclaimed Task
(a) pre edge b on a start-to-start            (b) pre edge a on b finish-to-start-next-day
both cases, the same:
  _batch claim template_task on a, b -> 200   edges: pre, ctl
  PUT Shot task_template=null        -> 200   edges: pre, ctl
  PUT Shot task_template=tt          -> 200, data.relationships.task_template = tt
                                              edges: ctl x on a, new b on a finish-to-start-next-day
  pre edge: GET -> 404, GET options[return_only]=retired -> 404
  ctl edge: GET -> 200
  Tasks on the Shot: 4, a b x made, c generated; Shot.task_template read back = tt
  upstream_tasks: a=[], b=[a], x=[a]
control: DELETE /entity/task_dependencies/<ctl> -> 204, then GET options[return_only]=retired -> 200
left clean: 0 Tasks, Shots, TaskTemplates zzprobe_101_*
```

**Teaches**
- **The template's edge wins.** In both cases the pre-existing edge is gone and the template's
  `b on a finish-to-start-next-day` stands in its place. No error, no skip, no duplicate, no loop.
- **The old row is erased, not retired.** It reads 404 under `options[return_only]=retired`, where a
  TaskDependency the caller DELETEs reads 200. No retired row is left to find; read the edges first.
- Nothing rolls back: the PUT is 200, `task_template` is stored, and the unclaimed template task `c`
  is generated. The caller learns of the swap only by reading the edges.
- An edge with a Task outside the template downstream of a claimed one (`x on a`) is kept. The
  reverse, a claimed Task depending on an outside Task, is erased (probes 107, 109). An edge between two
  claimed Tasks that the template does not link either way is deleted (probe 102).
