---
intent: Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write
tags: [write, status, task, version, shot, schema, batch, filter, silent]
endpoints: [GET /entity/<type>/<id>, GET /schema/<Type>/fields/<field>, POST /entity/<type>/_search, POST /entity/_batch]
scope: api
measured: first sample project read, sandbox project written
---

# 005_propagate_status

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT           # adds the bearer token and the /api/v1 prefix
from sg_groundtruth.env import load

c = FPT.from_env(load("."))                     # FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}   # array filters need it (probe 004)

PROJECT_ID = 1180                               # the caller supplies these four
PARENTS = [("Shot", 7563), ("Shot", 7564)]      # the parents to recompute
TRIGGER = ("Task", 46694)                       # the row whose status change started this run
PARENT_DONE, PARENT_WIP = "fin", "ip"           # both must appear in usable("Shot")


def slug(entity_type):
    return entity_type.lower() + "s"


# 1. The status vocabulary this project can actually use: valid_values minus hidden_values, read
#    with project_id (probe 009). Deriving the sets from the schema is what makes the rule portable:
#    a code the site adds joins them without a code change here.
def usable(entity_type, field="sg_status_list"):
    p = c.get(f"/schema/{entity_type}/fields/{field}",
              params={"project_id": PROJECT_ID}).json()["data"]["properties"]
    valid = (p.get("valid_values") or {}).get("value") or []
    hidden = (p.get("hidden_values") or {}).get("value") or []
    return [v for v in valid if v not in hidden]


FINISHED = {"Task": ["fin", "apr", "omt"], "Version": ["fin", "apr", "cmpt"]}
done = {t: [s for s in FINISHED[t] if s in usable(t)] for t in FINISHED}
blocking = {t: [s for s in usable(t) if s not in done[t]] for t in FINISHED}   # "all except these"


# 2. Every sibling of one parent in one call. `entity` is the owning link on Task and on Version
#    (entity_types/Task). A parent with more than 500 children needs paging: page until `data` is
#    empty, never on a missing `links.next` (probe 006).
def children(child_slug, parent_type, parent_id, ident):
    r = c.post(f"/entity/{child_slug}/_search", headers=ARR, json={
        "filters": [["entity", "is", {"type": parent_type, "id": parent_id}]],
        "fields": [ident, "sg_status_list"], "page": {"size": 500}})
    if not r.ok:
        raise SystemExit(json.dumps(r.json()["errors"], indent=2))
    return [row["attributes"]["sg_status_list"] for row in r.json()["data"]]


def status_of(entity_slug, entity_id):
    d = c.get(f"/entity/{entity_slug}/{entity_id}", params={"fields": "sg_status_list"}).json()
    return d["data"]["attributes"]["sg_status_list"]


# 3. The rule is over the whole sibling set, never over the row that triggered the run, and a
#    sibling counts as finished only by being in `done`. Testing `not in blocking` is wrong: a
#    sibling can hold a code that is in neither set (see Notes).
def decide(parent_type, parent_id):
    tasks = children("tasks", parent_type, parent_id, "content")        # Task identity is `content`
    versions = children("versions", parent_type, parent_id, "code")
    finished = (bool(tasks) and all(s in done["Task"] for s in tasks)
                and all(s in done["Version"] for s in versions))
    return PARENT_DONE if finished else PARENT_WIP


# 4. Decide, then re-read the trigger. If it moved while the siblings were being queried, the
#    decision was taken against a state that no longer exists: abandon and let the next run decide.
before = status_of(slug(TRIGGER[0]), TRIGGER[1])
wanted = {p: decide(*p) for p in PARENTS}
if status_of(slug(TRIGGER[0]), TRIGGER[1]) != before:
    raise SystemExit("trigger moved between the decision and the write; recompute")

# 5. One write for every parent that is not already there. Skipping the no-op write keeps the
#    propagation from feeding on its own EventLogEntry rows (probe 025).
reqs = [{"request_type": "update", "entity": t, "record_id": i,
         "data": {"sg_status_list": wanted[(t, i)]}}
        for t, i in PARENTS if wanted[(t, i)] != status_of(slug(t), i)]
if reqs:
    r = c.post("/entity/_batch", json={"requests": reqs})   # plain application/json (recipe 002)
    if not r.ok:
        raise SystemExit(json.dumps(r.json()["errors"], indent=2))   # nothing was applied

# 6. A write is confirmed by re-reading the row, never by its status code (probe 028).
for t, i in PARENTS:
    got = status_of(slug(t), i)
    print(t, i, "wanted", wanted[(t, i)], "reads back", got, got == wanted[(t, i)])
```

## Response

On the probed site, in one project:

```
1. GET /schema/Task/fields/sg_status_list?project_id=1180
     valid  ['wtg', 'ip', 'fin', 'apr', 'dis', 'na', 'hld', 'rev', 'omt', 'ready']
     hidden ['blk', 'hld', 'na', 'rdy', 'rev']    usable ['wtg', 'ip', 'fin', 'apr', 'dis', 'omt', 'ready']
     Version usable ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm']
     Shot    usable ['wtg', 'ip', 'fin', 'rev', 'apr', 'hld', 'omt']
     done     Task ['fin', 'apr', 'omt']            Version ['fin', 'apr', 'cmpt']
     blocking Task ['wtg', 'ip', 'dis', 'ready']    4 codes, the same list the project's UI offers

2. POST /entity/tasks/_search     [["entity", "is", {"type": "Shot", "id": 7563}]]  200, 3 rows
   POST /entity/versions/_search  the same filter                                   200, 0 rows

3. shot 7563  tasks ['fin', 'fin', 'wtg']  versions []       not done ['wtg']  -> 'ip'
   shot 7564  tasks ['fin', 'fin', 'fin']  versions ['rev']  not done ['rev']  -> 'ip'
   the trigger alone said 'wtg'; the parent's answer comes from all three siblings

4. decided on 'wtg'; the re-read immediately before the write says 'fin'  -> abandon
     the parent is untouched: still 'ip'
   recomputed from all siblings ['fin', 'fin', 'fin'] -> 'fin'; second read 'fin' == 'fin' -> proceed

5. POST /entity/_batch  2 updates  200 in 474ms      the same two as individual PUTs: 857ms
     Shot 7563 sg_status_list 'fin'    Shot 7564 sg_status_list 'ip'

6. Shot 7563 wanted 'fin' reads back 'fin' True
   Shot 7564 wanted 'ip'  reads back 'ip'  True
```

## Notes

- **The trigger is not the rule.** A run started by one Task changing answers "do all siblings satisfy
  the condition now", so the sibling set is re-queried in full and the triggering row's own status is
  used for nothing but the guard in step 4.
- **Two child types are two calls.** `_search` is per entity type, so a rule over Tasks and Versions
  queries `/entity/tasks/_search` and `/entity/versions/_search` with the same `entity` filter. One
  call per child type per parent, not one per row.
- **Many parents in one call.** `["entity", "in", [{"type": "Shot", "id": a}, {"type": "Shot", "id": b}]]`
  is accepted at 200, as is `["entity.Shot.id", "in", [a, b]]`. Ask for `entity` in `fields` and group
  the rows by `relationships.entity.data.id` yourself, then pair that with the batch write in step 5.
- **A sibling can hold a status outside `usable`.** REST does not enforce `hidden_values`
  (`field_types/status_list`), so a code the project hides writes and reads back fine. On the probed
  site `hld` is hidden on Task in this project and `PUT {"sg_status_list": "hld"}` answered 200 and
  read back `hld`. The two spellings of the rule then disagree over the same siblings
  `['fin', 'fin', 'hld']`:

  | rule | result | parent |
  |---|---|---|
  | `all(s in done)` | `False` | `ip`, correct |
  | `not any(s in blocking)` | `True` | `fin`, wrong: `blocking` was built from `usable`, which excludes `hld` |

  Build the "every status except these" set from the schema for the operator-facing list, and decide
  with `in done` so an unknown or hidden code blocks instead of passing.
- **`hidden_values` can name codes that are not in `valid_values`.** On the probed site the project
  hides `['blk', 'hld', 'na', 'rdy', 'rev']` on Task while `valid_values` holds no `blk` and no `rdy`;
  `PUT {"sg_status_list": "blk"}` is 400. Subtracting one list from the other is still correct, and
  the difference is not the set of writable codes.
- **Display labels fail two different ways.** `PUT {"sg_status_list": "Final"}` is a 400 that names the
  legal set, and the same string in a filter is a silent 0 rows:

      400 {"status": 400, "code": 104, "source": null, "detail": null, "meta": null,
           "title": "Update failed for [Task.sg_status_list]: 'Final' is not a valid status.
                     Valid statuses: 'wtg', 'ip', 'fin', 'apr', 'dis', 'na', 'hld', 'rev', 'omt', 'ready'."}

  The 400 enumerates site-wide `valid_values`, hidden codes included. Round-trip through
  `display_values` for anything an operator reads and send the code everywhere else.
- **The read-then-write race has no server-side guard.** The step 4 comparison narrows the window; it
  does not close it, and there is no conditional write to close it with:

  | sent on `PUT /entity/tasks/{id}` | result |
  |---|---|
  | `If-Match: "zzstale"` | 200, applied |
  | `If-Unmodified-Since: Mon, 01 Jan 1990 00:00:00 GMT` | 200, applied |
  | `If-None-Match: *` | 200, applied |
  | `updated_at` echoed back in the body | 400 `API update() Task.updated_at is editable on create only.` |

  A `GET` does return a weak `ETag` (`W/"6829a03d..."`), and no verb honours it. Two propagations
  racing over one parent both write; the last one wins, and the loser leaves no trace. Serialise the
  runs per parent on your side if the answer has to be exact.
- **Batch is worth it for the write half only.** The decision is reads, which `_batch` does not do.
  On the probed site two parent updates answered in 474ms as one batch against 857ms as two `PUT`s,
  one failing row rolls the whole call back, and the rows come back in request order. Recipe 002 has
  the contract, the size limits and the rollback matrix.
- A batch update row returns the whole record including the new `sg_status_list`, and it is still not
  the confirmation: `?fields` is ignored on every write (probe 024) and a write can be a 200 no-op
  (probe 028). Step 6 is the confirmation.
