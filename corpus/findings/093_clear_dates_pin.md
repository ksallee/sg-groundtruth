---
tags: [dependency, task, date]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 6 Tasks in one fan-out made and deleted; 19.1 s, 46 calls
verdict: On a dependent Task a start_date write pins it, null or real; a due_date write never does, null or real. A pinned null Task holds; PUT pinned:false refills both dates.
---

# 093_clear_dates_pin

**Q** Does clearing `start_date` and `due_date` on a Task (writing both to null) pin it?

**Endpoint** `PUT /entity/tasks/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent. `entity_types/Task` and probe 087 established that writing a dependent's own
dates pins it; neither says whether a `null` counts as a write, or which date does it.

**Actual** Provisioned by the probe: one upstream `up`, five dependents on it (`finish-to-start-next-day`),
all created 2026-03-02..03-03; the server then moved every dependent to 03-04..03-05. Each dependent
gets one write, then `up` moves to 03-09..03-10. Controls `sreal`/`dreal` write a real date.

```
                         both        start       due         sreal       dreal
first read (linked)      pin=False   pin=False   pin=False   pin=False   pin=False
PUT each                 start,due   start=null  due=null    start=03-05 due=03-06
                         =null
after                    None..None  None..03-05 03-04..None 03-05..03-06 03-04..03-06
                         pin=True    pin=True    pin=False   pin=True    pin=False dur 960->1440
PUT up 03-09..03-10      held        held        03-11..03-12 held,      03-11..03-13
                         viol=False  viol=False  pin=False   viol=True   pin=False
PUT due due=03-20 (control, same Task)           03-11..03-20 dur=3840 pin=False
PUT due start=03-16 (control, same Task)         03-16..03-25 pin=True
PUT each pinned=false    03-11..03-12 03-11..03-12 03-11..03-20 03-11..03-12 03-11..03-13
                         all pin=False, viol=False
left clean: 0 Tasks, 0 TaskDependency rows
```

**Teaches**

| write on a dependent Task | `pinned` after | on the next upstream write |
|---|---|---|
| `start_date` null, alone or with `due_date` | `true` | held; the null stays null, `dependency_violation` stays `false` |
| `start_date` real | `true` (control) | held; `dependency_violation` `true` |
| `due_date` null alone | `false` | follows: both dates rewritten from the upstream and `duration` |
| `due_date` real | `false` (control, twice); `duration` recomputed | follows, new `duration` kept |
| `PUT {"pinned": false}` | `false` | rewrites `start_date` from the upstream, `due_date` from `duration` |

- **`start_date` is the pinning write, not "any date".** The same Task (`due`) stayed unpinned after
  `due_date` null and after a real `due_date`, then pinned on a real `start_date`. A `due_date` write
  acts like a `duration` write (probe 100): it resizes, it does not anchor.
- Nothing unpins a Task by itself: `both` and `start` stayed pinned with a null start across the
  upstream move. A null start raises no `dependency_violation`, so it is invisible to a violation check.
- `duration` survives every null write (960 throughout); the unpin recompute uses it to refill `due_date`.
- A sync that wants the server to reschedule a Task sets `pinned: false`; nulling the dates either pins
  it (`start_date`) or is overwritten at the next upstream write (`due_date`).
