---
tags: [batch, multi-entity, write]
endpoints: [POST /entity/_batch, GET /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2026-11-17; 3 Shots and 7 Notes, all deleted
verdict: `multi_entity_update_mode` in a `_batch` update's `data` adds, removes and sets as on a PUT, and several updates of one record in one batch apply in request order, each row echoing the state after it.
---

# 154_batch_multi_entity_mode

**Q** Does a multi_entity add or remove with `multi_entity_update_mode` in the body work inside a
`_batch` update, and do two updates of one record in one batch apply in request order?

**Endpoint** `POST /entity/_batch`

**Docs claim** Silent on update modes in a batch. Recipe 009 measured the mode on a single `PUT`;
recipe 002 measured batch updates of plain fields.

**Actual**

```
Note.note_links starts at [S1] for every case; one POST /entity/_batch per case
{"request_type": "update", "entity": "Note", "record_id": N,
 "data": {"note_links": {"multi_entity_update_mode": "add", "value": [S2]}}}

requests in the batch            status  reads back    each row's note_links
add [S2]                         200     [S1, S2]      [S1, S2]
remove [S1]                      200     []            []
bare list [S2]                   200     [S2]          [S2]
add [S3], remove [S1]            200     [S3]          [S1, S3], [S3]
set [S2], add [S3]               200     [S2, S3]      [S2], [S2, S3]
add [S3], set [S2]               200     [S2]          [S1, S3], [S2]
content "first", "second"        200     "second"      [S1], [S1]
```

**Teaches**
- Write the mode inside `data` exactly as in a `PUT` body (recipe 009). A bare list still replaces the
  set, in a batch as on a `PUT`.
- Requests on one record run in order, each on the result of the one before: `add` then `set` ends at
  the `set`, `set` then `add` keeps both. Each result row is the whole record after that request
  (recipe 002), so the last row for a record is its final state.
- Several link edits to one row can share a batch with no read in between.
