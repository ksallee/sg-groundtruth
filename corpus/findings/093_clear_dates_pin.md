---
tags: [dependency, task, date]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 2 Tasks in one chain made and deleted; wall time and call count unrecorded
verdict: A null write on a dependent Task's start_date or due_date pins it exactly like a real date; duration is held. Only PUT pinned:false recomputes the nulled date(s) from the dependency.
---

# 093_clear_dates_pin

**Q** Does clearing `start_date` and `due_date` on a Task (writing both to null) pin it?

**Endpoint** `PUT /entity/tasks/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent. `entity_types/Task` and probe 087 established that writing a dependent's own
dates pins it; neither says whether a `null` counts as a write.

**Actual**

```
linked: up -FS-> down, both created 03-02..03-03, down unpinned
PUT down start_date=null, due_date=null
                down None..None  dur=960  pinned=True
PUT up 03-09..03-10 (moved later)
                up 03-09..03-10  down None..None  dur=960  pinned=True (held)
PUT down pinned=false
                down 03-11..03-12  dur=960  pinned=False   <- recomputed from null
PUT down start_date=null only (due_date left 03-12)
                down None..03-12  dur=960  pinned=True
PUT up due_date=03-16
                up 03-09..03-16  down None..03-12  dur=960  pinned=True (held)
PUT down pinned=false
                down 03-17..03-18  dur=960  pinned=False   <- both fields recomputed, not just start
PUT down due_date=null only (start_date left 03-17)
                down 03-17..None  dur=960  pinned=True
PUT up start_date=03-20
                up 03-20..03-27  down 03-30..03-31  pinned=False (followed, unpinned)
```

**Teaches**

| write on the dependent | result |
|---|---|
| `{"start_date": null, "due_date": null}` | `pinned` -> `true`, same as a real date write |
| one field null, the other untouched | also pins; the untouched field keeps its old value, not null |
| upstream moves while pinned, dates null | dependent holds `None`/`None`, does not recompute or follow |
| `duration` | held across every null write; never cleared or recomputed alongside the dates |
| `PUT {"pinned": false}` | rewrites **both** dates from the dependency at once, even when only one was null |

- A `null` is a write, not an absence: the field that goes null is exactly as pinning as a real date,
  confirming `entity_types/Task`'s "writing a dependent's own dates pins it" for the clear case too.
- Clearing does not put a Task into a distinguishable "waiting to be scheduled" state. It is `pinned`
  with a hole in it, and the hole does not fill itself; only unpinning triggers the recompute, and that
  recompute ignores the surviving field, overwriting it along with the null one (see probe 087, where
  the same unpin snapped a dependent back behind its upstream).
- A sync that wants the server to reschedule a Task must set `pinned: false`, not merely null the dates.
