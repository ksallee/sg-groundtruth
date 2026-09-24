---
tags: [dependency, task, duration]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 3 Tasks in one chain made and deleted; wall time and call count unrecorded
verdict: Writing duration on a dependent Task does not pin it, unlike a date write (087, 093). It stays unpinned and keeps following the upstream, on both ends of the chain.
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

```
up -FS-> down -FS-> down2; every Task written 2026-03-02..03-03 (dur=960)
linked             up 03-02..03-03  down 03-04..03-05        down2 03-06..03-09
PUT down duration=1920 (dates left alone)  -> 200
                    up 03-02..03-03  down 03-04..03-09 dur=1920  down2 03-10..03-11  pinned=False
PUT up due_date=03-10 (later)              -> 200
                    up 03-02..03-10  down 03-11..03-16 dur=1920  down2 03-17..03-18  pinned=False
PUT down pinned=false (already false, no-op) -> 200, nothing changed
PUT up duration=2880 (upstream)            -> 200
                    up 03-02..03-09  down 03-10..03-13 dur=1920  down2 03-16..03-17  pinned=False
```

**Teaches**

| write | effect on the dependent (`down`) |
|---|---|
| `duration` alone on `down` | `pinned` stays `false`; `start_date` recomputes to the day after the upstream ends, `due_date` stretches to hold the new `duration` |
| upstream moves later, after that | `down` moves with it, `duration` held at 1920: an unpinned dependent, whether or not `duration` was ever written on it |
| `duration` on the upstream (`up`) | `down` and `down2` both move to absorb the shorter/longer upstream span, same as a date write (087) |

- `duration` is not one of the fields that pins. Only a write to `start_date` or `due_date` on the
  dependent itself sets `pinned` (`entity_types/Task`, probe 087, probe 093); writing `duration` there
  recomputes `start_date`/`due_date` from the dependency exactly as it would on an unlinked Task, and
  the Task keeps following its upstream on every later write.
- `down2` moved on every step, including the `duration`-only write to `down`: a dependent's own
  `duration` write cascades downstream the same as a date write does.
- Writing `duration` on the upstream end reschedules every unpinned downstream Task, confirming probe
  087's date-based finding also holds for the third leg of the `start_date`/`due_date`/`duration`
  triple.
