---
tags: [dependency, task, duration]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 4 Tasks (3 chained, 1 unlinked) made and deleted; 12.5 s, 31 calls
verdict: Writing duration on a dependent Task does not pin it; a start_date write in the same run does. It keeps following the upstream, and a duration write upstream moves it.
---

# 100_duration_write_pin

**Q** Does writing `duration` on a dependent Task pin it, the way a date write does? What happens to
its `start_date`/`due_date`, and does it still follow the upstream afterwards? Does writing `duration`
on the upstream Task move its downstream Tasks?

**Endpoint** `PUT /entity/tasks/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent, as for every scheduling field. `entity_types/Task` and probe 087 cover date
writes on both ends of a chain; probe 093 covers nulling a dependent's dates. Neither writes `duration`
alone.

**Actual**

The probe provisions everything: one Shot, four Tasks, two TaskDependency rows, all deleted on exit
(read back: 0 Tasks, 0 Shots, 0 live TaskDependency rows).

```
up -FS-> down -FS-> down2; solo has no edge; every Task written 2026-03-02..03-03 (dur=960)
linked                          up 03-02..03-03  down 03-04..03-05  down2 03-06..03-09  solo 03-02..03-03
PUT solo duration=1920 (no edges)       -> 200   solo 03-02..03-05 dur=1920 pinned=False; chain unchanged
PUT down duration=1920 (dates left alone) -> 200
                                up 03-02..03-03  down 03-04..03-09 dur=1920  down2 03-10..03-11  pinned=False
PUT up due_date=03-10 (later)           -> 200
                                up 03-02..03-10  down 03-11..03-16 dur=1920  down2 03-17..03-18  pinned=False
PUT down pinned=false (already false)   -> 200, nothing changed
PUT up duration=2880 (upstream)         -> 200
                                up 03-02..03-09  down 03-10..03-13 dur=1920  down2 03-16..03-17  pinned=False
PUT down start_date=03-20 (control)     -> 200
                                up 03-02..03-09  down 03-20..03-25 dur=1920 pinned=True  down2 03-26..03-27
violation=False on every Task at every step
```

**Teaches**

| write | effect on the dependent (`down`) |
|---|---|
| `duration` alone on an unlinked Task (`solo`) | `pinned` stays `false`; `start_date` kept, `due_date` stretches to hold the new `duration` |
| `duration` alone on `down` | the same: `pinned` stays `false`, `start_date` kept (already the day after the upstream ends), `due_date` stretches |
| upstream moves later, after that | `down` moves with it, `duration` held at 1920 |
| `duration` on the upstream (`up`) | `up`'s `due_date` moves; `down` and `down2` follow it, same as a date write (087) |
| `start_date` on `down` (control) | `pinned` turns `true`; `duration` held, `due_date` moves; `down2` follows |

- `duration` does not pin. In the same run a `start_date` write on `down` did. `due_date` was not
  written on the dependent here; that it pins too rests on `entity_types/Task`, 087 and 093.
- On the dependent, a `duration` write keeps `start_date` and moves `due_date`, the same as on the
  unlinked `solo`. The dependent then keeps following its upstream.
- `down2` moved on every write that moved `down`, the `duration`-only write included: a dependent's own
  `duration` write cascades downstream. It stayed put on the no-op `pinned=false` write, where nothing
  moved.
- Writing `duration` on the upstream end reschedules every unpinned downstream Task, so probe 087's
  date-based finding holds for `duration` too.
