---
tags: [dependency, task, date]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 1 Shot, 3 Tasks and 1 TaskDependency made and deleted; 11.9 s, 31 calls
verdict: A Task with no upstream never pins, on a null or a real date write; nulling its dates leaves its downstream unmoved, and pinned:false refills nothing.
---

# 097_null_dates_unpin

**Q** For a Task with no upstream edge, does clearing `start_date`/`due_date` pin it the way 093 found
for a dependent, does `PUT {"pinned": false}` afterwards fill the nulls back in, what wins when the nulls
and `pinned: false` are sent in one PUT, and do its downstream Tasks move? Controls: a real date write
on the same Tasks, reading `pinned` and the downstream back.

**Endpoint** `PUT /entity/tasks/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent, as for 087 and 093. `pinned` is untyped beyond `checkbox`.

**Actual**

```
iso: no edges at all, created 03-02..03-03. Every PUT below answered 200.
PUT iso start=null due=null -> iso None..None dur=960 pinned=False violation=False
PUT iso pinned=false        -> iso None..None dur=960 pinned=False   <- no change, nothing to recompute
PUT iso {start=null,due=null,pinned=false} in ONE put
                            -> iso None..None dur=960 pinned=False   <- same as the null alone
PUT iso start=03-09 due=03-10 (control)
                            -> iso 03-09..03-10 dur=960 pinned=False <- a real date does not pin it either

root -FS-> down, both written 03-02..03-03, down scheduled to 03-04..03-05
PUT root start=null due=null
                     -> root None..None  down 03-04..03-05 (unmoved) pinned=False both
PUT root pinned=false
                     -> root None..None  down 03-04..03-05 (unmoved) pinned=False   <- root never refills
PUT root {start=null,due=null,pinned=false} in ONE put
                     -> root None..None  down 03-04..03-05 (unmoved) pinned=False
PUT root start=03-09 due=03-10 (control)
                     -> root 03-09..03-10 pinned=False  down 03-11..03-12 (moved) pinned=False

left clean: 0 zzprobe_097 Tasks, the TaskDependency row gone
```

**Teaches**

| the Task | after a date write |
|---|---|
| no edges, dates set `null` | `pinned` stays `false`; a null write only pins a Task that has an upstream (093, `entity_types/Task`) |
| no edges, real dates | `pinned` stays `false` |
| upstream-only (has downstream, no upstream), `null` or real dates | `pinned` stays `false` |
| its `finish-to-start` downstream | unmoved by the `null` write; moved by the real one (03-11..03-12), as in 087 |

- **Only a Task with an upstream pins on a date write.** Here neither a `null` nor a real date write set
  `pinned` on a Task with no upstream, with or without a downstream. 087 and 093 measured the pin on
  dependents.
- `PUT {"pinned": false}` on a Task that was already `false` is a no-op: the nulls survive it. No
  fallback anchor filled them: not `duration`, not a project date, not today.
- Sending the nulls and `pinned: false` in one `PUT` read back the same as the nulls alone.
- A `null` upstream leaves the downstream's stored dates where they were; the next real date write on
  the same upstream moves it again. The edge still schedules; a `null` gives it nothing to schedule from.
- A client that wants a Task to go back to "server picks the date" has no move here: clearing a
  root Task's dates is a dead end, not a pending state. It stays `null`/`null` until something writes a
  real date onto it.
