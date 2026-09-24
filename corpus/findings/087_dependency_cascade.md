---
tags: [dependency, task, date]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 5 Tasks in one chain made and deleted
verdict: An upstream date write reschedules every unpinned downstream Task, later and earlier alike; a null one moves none (097). A pinned Task stays put and flags `dependency_violation` while broken.
---

# 087_dependency_cascade

**Q** When an upstream Task's dates move, which downstream Tasks move with it, and does `pinned` stop it?

**Endpoint** `PUT /entity/tasks/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent on scheduling. The schema types `pinned` and `dependency_violation` as
`checkbox` fields and describes neither.

**Actual**

```
up -FS-> d1 -FS-> d2,  up -FS-> pin,  up -SS-> ss; every Task written as 2026-03-02..03-03
linked            up 03-02..03-03  d1 03-04..03-05  d2 03-06..03-09  pin 03-04..03-05  ss 03-02..03-03
PUT pin pinned=true -> 200
up due 03-05      up 03-02..03-05  d1 03-06..03-09  d2 03-10..03-11  pin 03-04..03-05 violation=True
up due 03-02      up 03-02..03-02  d1 03-03..03-04  d2 03-05..03-06  pin 03-04..03-05 violation=False
up start 03-09    up 03-09..03-09  d1 03-10..03-11  d2 03-12..03-13  pin (held) violation=True  ss 03-09..03-10
up duration 2400  up 03-09..03-13  d1 03-16..03-17  d2 03-18..03-19  pin (held) violation=True
PUT d1 03-02..03-03 (before up ends)
                  d1 03-02..03-03 pinned=True violation=True   d2 03-04..03-05 (followed d1)
PUT d1 pinned=false
                  d1 03-16..03-17 pinned=False violation=False d2 03-18..03-19
up due 03-20      up 03-09..03-20  d1 03-23..03-24  d2 03-25..03-26  pin (held) violation=True
```

**Teaches**

| the downstream Task | after an upstream date write |
|---|---|
| unpinned, any depth | moved to satisfy its dependency, later or earlier, `duration` held |
| `start-to-start` | follows the upstream start; untouched by a due date write |
| `pinned` true | dates held; `dependency_violation` true while broken, false again once satisfied |
| downstream of a pinned Task | follows the pinned Task, not the upstream end of the chain |
| any, when the upstream's dates are written `null` | unmoved: keeps its dates (probe 097) |

- **The cascade pulls back as well as pushes.** Shortening the upstream moved d1 and d2 earlier. A Task
  whose dates a person chose and did not pin is overwritten by any upstream write, and by a new edge
  (probe 092).
- **Writing a dependent's own dates pins it.** The date `PUT` on d1 set `pinned` true (as
  `entity_types/Task` found) and d2 followed d1 to a date before the upstream ends. A `null` date pins
  it too (probe 093); a `duration` write does not (probe 100); a Task with no upstream never pins (probe 097).
- `PUT {"pinned": false}` reschedules at once: d1 snapped back behind the upstream and d2 with it.
- `pinned` is writable directly, so a sync can protect a Task before it rewrites the upstream end.
