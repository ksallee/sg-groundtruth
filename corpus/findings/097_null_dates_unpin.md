---
tags: [dependency, task, date]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 3 Tasks made and deleted (1 isolated, 1 root, 1 downstream); 10.2 s, 20 calls
verdict: A Task with no upstream edge never pins on a null date write: pinned stays false, its downstream Tasks hold their dates, and pinned:false has nothing to recompute either null from.
---

# 097_null_dates_unpin

**Q** For a Task with no upstream edge, does clearing `start_date`/`due_date` pin it the way 093 found
for a dependent, does `PUT {"pinned": false}` afterwards fill the nulls back in, what wins when the nulls
and `pinned: false` are sent in one PUT, and do its downstream Tasks move?

**Endpoint** `PUT /entity/tasks/<id> ; POST /entity/tasks/_search`

**Docs claim** Silent, as for 087 and 093. `pinned` is untyped beyond `checkbox`.

**Actual**

```
iso: no edges at all, created 03-02..03-03
PUT iso start=null due=null -> iso None..None dur=960 pinned=False violation=False
PUT iso pinned=false        -> iso None..None dur=960 pinned=False   <- no change, nothing to recompute
PUT iso {start=null,due=null,pinned=false} in ONE put
                             -> iso None..None dur=960 pinned=False   <- same as the null alone

root -FS-> down, both 03-02..03-03, down auto-scheduled to 03-04..03-05
PUT root start=null due=null
                     -> root None..None  down 03-04..03-05 (unmoved) pinned=False both
PUT root pinned=false
                     -> root None..None  down 03-04..03-05 (unmoved) pinned=False   <- root never refills
PUT root {start=null,due=null,pinned=false} in ONE put
                     -> root None..None  down 03-04..03-05 (unmoved) pinned=False

```

**Teaches**

| the Task | after `start_date`/`due_date` both set to `null` |
|---|---|
| no edges | `pinned` stays `false`; a null write only pins a Task that has an upstream (093, `entity_types/Task`) |
| upstream-only (has downstream, no upstream) | same: `pinned` stays `false` |
| its downstream Task | keeps its already-computed dates; a null upstream does not clear, recompute or move it |

- **`pinned` is a dependency concept, not a date-write concept.** 093 showed a null write pins a
  dependent because it conflicts with what the upstream would compute for it. A Task with nothing
  upstream has no computed value to conflict with, so the same null write leaves `pinned` at `false`.
- `PUT {"pinned": false}` on a Task that was already `false` is a no-op: the nulls survive it. There is
  no fallback anchor (not `duration`, not a project date, not today) because unpinning only ever
  triggers the recompute-from-dependency 087 and 093 measured, and there is no dependency to recompute
  from.
- Sending the nulls and `pinned: false` in one `PUT` changes nothing here: with no upstream, neither
  key does anything the other key would contest, so there is no winner to report.
- A downstream Task is scheduled once, off its upstream's dates at link time (`entity_types/Task`). It
  does not re-derive from a live read of the upstream on every fetch: nulling the upstream leaves the
  downstream's own stored dates untouched, unlike a real date move (087), which does cascade.
- A client that wants a Task to go back to "server picks the date" has no move here: clearing a
  root Task's dates is a dead end, not a pending state. It stays `null`/`null` until something writes a
  real date onto it.
