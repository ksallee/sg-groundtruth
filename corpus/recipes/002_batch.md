---
intent: Apply many creates, updates and deletes in one atomic call, and match the results back to the requests
tags: [write, batch, create, version, shot, error-handling, silent]
endpoints: [POST /entity/_batch]
scope: api
measured: sandbox project, every row created and deleted
---

# 002_batch

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT           # adds the bearer token and the /api/v1 prefix
from sg_groundtruth.env import load

c = FPT.from_env(load("."))                     # FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
PROJECT_ID = 1234                               # the caller supplies this


def run(requests_):
    """One atomic call. Plain application/json; the vendor type _search needs 415s here."""
    r = c.post("/entity/_batch", json={"requests": requests_})
    if not r.ok:
        raise SystemExit(json.dumps(r.json()["errors"], indent=2))   # nothing was applied
    return r.json()["data"]


def row_id(row):
    """A create or update row nests the record under `data`; a delete row is flat."""
    return row.get("data", row)["id"]


# 1. A batch cannot reference an id it creates, so the rows the rest of the batch points at
#    go in a call of their own.
shot_id = row_id(run([{"request_type": "create", "entity": "Shot",
                       "data": {"project": {"type": "Project", "id": PROJECT_ID},
                                "code": "sh010", "description": "batch 1"}}])[0])

# 2. Two creates and an update of another entity type, in one call. `entity` is the singular
#    schema name and the id key is `record_id`.
reqs = [
    {"request_type": "create", "entity": "Version",
     "data": {"project": {"type": "Project", "id": PROJECT_ID}, "code": "v001",
              "entity": {"type": "Shot", "id": shot_id}, "sg_status_list": "rev"}},
    {"request_type": "create", "entity": "Version",
     "data": {"project": {"type": "Project", "id": PROJECT_ID}, "code": "v002",
              "entity": {"type": "Shot", "id": shot_id}, "sg_status_list": "rev"}},
    {"request_type": "update", "entity": "Shot", "record_id": shot_id,
     "data": {"description": "batch 2"}},
]
out = run(reqs)

# 3. Results are one row per request, in request order. Pair them by position: two rows can share
#    a code, and matching on one would mislink them.
ids = [row_id(row) for row in out]
for req, i in zip(reqs, ids):
    print(req["request_type"], req["entity"], i)

# 4. Delete takes record_id and no data. Mixed types are fine in one call.
run([{"request_type": "delete", "entity": "Version", "record_id": ids[0]},
     {"request_type": "delete", "entity": "Version", "record_id": ids[1]},
     {"request_type": "delete", "entity": "Shot", "record_id": shot_id}])
```

## Response

```
1. batch 1  200  [{"data": {"type": "Shot", "id": 7557, "attributes": {...}, "links": {...}}}]
2. batch 2  200, three rows, in request order
     row 0  create  keys ['data']                    Version 29926  code 'v001'
     row 1  create  keys ['data']                    Version 29927  code 'v002'
     row 2  update  keys ['data', 'links', 'status'] Shot    7557   description 'batch 2'
   row 0 in full, trimmed:
     {"data": {"type": "Version", "id": 29926,
               "attributes": {"code": "v001", "sg_status_list": "rev", "cached_display_name": "v001",
                              "created_at": "2026-09-02 19:07:26 UTC", "viewed_by_current_user": "unread",
                              "updated_at": "2026-09-02 19:07:26 UTC", "open_notes_count": 0,
                              "sg_version_type": "Type A"},
               "relationships": {"entity": {...}, "project": {...}, "tasks": {"data": []}, ...},
               "links": {"self": "/api/v1/entity/versions/29926"}}}
3. step 3 prints
     create Version 29926
     create Version 29927
     update Shot 7557
4. delete  200, one flat row per request. One of them verbatim:
     {"request_type": "delete", "type": "Version", "id": 29941,
      "uuid": "906c4522-a701-11f1-b496-0a58a9feac02", "did_delete": true}
```

## Notes

- **A batch cannot use an id it creates.** Every way of pointing request 1 at request 0's row was
  rejected, and the failure is the whole batch, so nothing at all lands.

  | `entity` value sent | result |
  |---|---|
  | `{"type": "Shot", "id": "$0"}` | 400 `Invalid field value, update failed [5 - Update failed for [Version.entity]: Value is not legal.]` |
  | `{"type": "Shot", "id": -1}` | 400, the same |
  | `{"type": "Shot", "id": "0"}` | 400, the same |
  | `{"type": "Shot", "id": "u1"}`, request 0 sent with `"uuid": "u1"` | 400, the same |
  | `{"type": "Shot", "uuid": "u1"}`, request 0 sent with `"uuid": "u1"` | 400 `Invalid field value, update failed [5 - Update failed for [Version.entity]: Invalid statement.]` |

  The `uuid` a delete row returns is generated per request and is not an input. Build a dependent
  graph as one batch per level: create the parents, read their ids out of the response, substitute,
  then send the children. Steps 1 and 2 above are that sequence.
- **Results are in request order**, one row per request, interleaved by neither id nor type. A batch of
  `[update 29926, create, update 29927, create, update Shot 7557]` answered in exactly that order, so
  `zip(requests, response["data"])` is correct and no key matching is needed. Two creates sending the same
  `code` came back as two rows distinguished only by position and by the new ids, 29930 and 29931.
- **One failing request rolls back every other one.** Each round below sent a good create, one bad
  request, and an update of an existing row whose `description` read `before`:

  | the bad request | status | after it |
  |---|---|---|
  | `update` `record_id` 999999999 | 404 `Entity of type [Version] with id=999999999 does not exist.` | 0 rows created, `description` still `before` |
  | `delete` `record_id` 999999999 | 404, the same | 0 rows created, `description` still `before` |
  | `create` with `sg_not_a_field` | 400 `Invalid field value, update failed [2 - Invalid field name: field [Version.sg_not_a_field] does not exist or user does not have access permission.]` | 0 rows created, `description` still `before` |
  | `create` with `sg_status_list: not_a_status` | 400 `Invalid field value, update failed [5 - Update failed for [Version.sg_status_list]: 'not_a_status' is not a valid status. Valid statuses: 'na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng'.]` | 0 rows created, `description` still `before` |

  The rollback is the reason to use the endpoint. A timeout is not covered by it: see the size note.
- **A batch create skips the validation a single create applies, and the row it makes is unreadable.**
  `POST /entity/versions` with no `project` is 400 `API create() missing 'project' attribute: {"code" => "v001"}`.
  The same create inside a batch answered 200 with `id` 29932 and a create row holding no `project`
  relationship. `GET /entity/versions/29932` then answered 404 `Version: 29932 not found`, and a site-wide
  `POST /entity/versions/_search` on its `code` returned 0 rows. `DELETE /entity/versions/29932` answered
  204, so the row exists and only the id from the create response can reach it. Validate a batch payload
  yourself; a 200 is not proof the row is addressable. A link to an id that does not exist is rejected on
  both paths, 400 `Update failed for [Version.entity]: Value is not legal.`
- **Size.** No cap was found. A `requests` array of 5001 was validated in full, answering one
  `data hash containing field/value pairs is required for the given request` per element. On the probed
  site a committing batch of 200 answered in 11.7s, 500 in 31.0s and 1001 in 47.7s on one run and not at
  all on another, where the client gave up at its own 60s read timeout. **All 1001 rows had committed
  anyway.** A read timeout tells you nothing about what landed, and there is no request id to ask about,
  so keep a batch inside the response window, around 200 requests, and make each chunk re-runnable by
  reading back on `code` before resending.
- **The contract, one 400 at a time.** Every rejection below names what it wanted.

  | sent | result |
  |---|---|
  | `Content-Type: application/vnd+shotgun.api3_array+json` | 415 `Unsupported Content-Type 'application/vnd+shotgun.api3_array+json'`, `{"content_type": "Content-Type must be one of: 'application/json'."}` |
  | a top-level array | 400 `Invalid JSON body. Expected Hash but received Array.` |
  | `{"entity": "Version"}` | 400 `Request Parameters invalid.` `{"requests": ["requests is missing"]}` |
  | `{"requests": []}` | 200 `{"data": []}` |
  | a request with no `entity` | 400 `{"requests": {"0": {"entity": ["entity is missing"]}}}` |
  | a `create` with no `data` | 400 `{"data": ["data hash containing field/value pairs is required for the given request"]}` |
  | `"request_type": "read"` | 400 `{"requests": {"0": {"request_type": ["request_type must be one of: create, update, delete"]}}}` |
  | `"entity": "versions"`, the URL slug | 400 `Invalid entity type: entity type [] does not exist.` |
  | `delete` with no `record_id`, or with `entity_id` | 404 `Entity of type [Version] with id=0 does not exist.` |
- **`delete` in a batch and the `DELETE` verb do the same thing and report it differently.**

  | | body | after it |
  |---|---|---|
  | batch `delete` | 200 `{"request_type": "delete", "type": "Version", "id": N, "uuid": "...", "did_delete": true}` | `GET` that id 404s |
  | `DELETE /entity/versions/N` | 204, 0 bytes | `GET` that id 404s |

  Deleting an already deleted id inside a batch is 404 `Entity of type [Version] with id=N does not exist.`
  and takes the rest of the batch down with it, so a delete pass is not idempotent.
- Response shape differs by `request_type`: a create row is the thin create subset, an update row is the
  whole record wrapped with `links` and `status`, a delete row is flat (probe 024 for the field-level
  table). `?fields` on `/entity/_batch` is accepted and ignored, as on every other write (probe 024), and
  no row resolves a dotted path, so re-read for those.
