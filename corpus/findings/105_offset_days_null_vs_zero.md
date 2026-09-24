---
tags: [task-template, dependency, trap]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>, PUT /entity/<type>/<id>, POST /entity/<type>/_search, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 1 template, 1 Shot, 10 Tasks, 8 edges made and deleted; 22.3 s, 61 calls, 2 runs agree
verdict: TaskDependency `offset_days` null and 0 are stored and compared as different: a template apply deletes an entity edge with null against a template 0 (or the reverse) and re-creates it with a new id.
---

# 105_offset_days_null_vs_zero

**Q** A TaskDependency created with `offset_days` null, 0, or the key omitted: what does each read back
as? And when a template edge holds 0 and the entity edge null (or the reverse) on the same pair, does
the apply of probe 102 keep the edge with its id, or delete and re-create it?

**Endpoint** `POST /entity/task_dependencies ; GET /entity/task_dependencies/<id> ; PUT /entity/task_dependencies/<id> ; PUT /entity/shots/<id> ; POST /entity/task_dependencies/_search`

**Docs claim** Silent. Probe 085 found null and 0 place the dependent Task on the same dates.

**Actual**

```
template tasks a..e, edges all finish-to-start-next-day on a
  b on a  sent offset_days=0        POST 201 response offset_days=0         GET offset_days=0
  c on a  sent offset_days=None     POST 201 response has no offset_days    GET offset_days=None
  d on a  sent offset_days=omitted  POST 201 response has no offset_days    GET offset_days=None
  e on a  sent offset_days=0        POST 201 response offset_days=0         GET offset_days=0
  _search offset_days is 0: [b, e]      _search offset_days is None: [c, d]

Shot, PUT task_template T -> 200; edges copied as the template holds them:
  copied            b1 off=0     c1 off=None   d1 off=None   e1 off=0
  PUT b1 offset_days=None, c1 offset_days=0, e1 offset_days=2 -> 200 each
  after edge PUTs   b1 off=None  c1 off=0      d1 off=None   e1 off=2     (same ids)
  PUT Shot task_template=None -> 200, edges unchanged, same ids
  PUT Shot task_template=T    -> 200
                    b1 off=0 NEW id  c1 off=None NEW id  d1 off=None same id  e1 off=0 NEW id
  first ids GET: b1 404, c1 404, d1 200, e1 404
left clean: 0 Tasks, 0 task_dependencies, 0 Shots, 0 TaskTemplates
```

**Teaches**
- **Null and 0 are two stored values.** A create with null or with the key omitted reads back null; a
  create with 0 reads back 0. `offset_days is 0` does not match a null row, and `is null` does not match a 0.
- **The apply compares them as different.** Template 0 against entity null, and template null against
  entity 0, both end with the entity edge deleted (GET 404) and re-created with the template's value and
  a new id, the same as a real difference (the `e1` control, 2 against 0). The unchanged `d1` kept its id.
- To keep edge ids through a re-apply, write `offset_days` exactly as the template holds it, null or 0,
  never one for the other. Anything keyed on a TaskDependency id loses it otherwise (probe 101: the old
  row is erased, not retired).
- The POST response omits `offset_days` when it is null; read it with a GET or a `_search`.
- Provisioned by the probe; no operator step. Only `finish-to-start-next-day` was measured, and the
  dates of null against 0 are probe 085's, not measured again here.
