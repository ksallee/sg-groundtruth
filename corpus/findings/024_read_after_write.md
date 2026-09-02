---
tags: [write, create, batch, upload, async, entity-field, trap]
scope: api
measured: first sample project read, sandbox project written
verdict: Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
---

# 024_read_after_write

**Q** What does a write return, and what must be re-read?

**Endpoint** `POST /entity/versions ; PUT /entity/versions/{id} ; POST /entity/_batch ; POST {field}/_upload complete_upload ; DELETE /entity/versions/{id}`

**Docs claim** The REST docs describe `?fields` on reads only, and document no batch endpoint at all.

**Actual**

```
asked for on every verb: ['code', 'description', 'sg_status_list', 'created_at', 'created_by',
                          'project.Project.name', 'entity.Shot.code', 'sg_not_a_field']
read   POST _search        200  absent: ['sg_not_a_field']            <- dotted paths resolve
create POST                201  attributes=9  relationships=15  absent: ['project.Project.name', 'entity.Shot.code', 'sg_not_a_field']
create POST ?fields=...    201  attributes=9  relationships=15  absent: the same three
create POST, 3 more fields 201  attributes=12 relationships=15
update PUT                 200  attributes=52 relationships=20  absent: the same three
update PUT ?fields=...     200  attributes=52 relationships=20  absent: the same three
update PATCH               404  {"status": 404, "code": 103, "title": "Not Found", "detail": null}
  relationships.entity, identical on create and update:
    {"data": {"id": 7514, "name": "sh010", "type": "Shot"}, "links": {"self": ..., "related": ...}}

POST /entity/_batch
  415 Unsupported Content-Type 'application/vnd+shotgun.api3_array+json'  {"content_type": "Content-Type must be one of: 'application/json'."}
  400 Invalid JSON body. Expected Hash but received Array.
  400 Request Parameters invalid. {"requests": ["requests is missing"]}
  400 Request Parameters invalid. {"requests": {"0": {"entity": ["entity is missing"]}}}
  400 Request Parameters invalid. {"data": ["data hash containing field/value pairs is required for the given request"]}
  400 Request Parameters invalid. {"requests": {"0": {"request_type": ["request_type must be one of: create, update, delete"]}}}
  404 update keyed on entity_id rather than record_id: "Entity of type [Version] with id=0 does not exist."
  200 create row  outer keys ['data']                    attributes=9  relationships=15
  200 update row  outer keys ['data', 'links', 'status'] attributes=52 relationships=20
  200 delete row  {"request_type": "delete", "type": "Version", "id": N, "uuid": "...", "did_delete": true}
  404 a good create + a bad update: "Entity of type [Version] with id=999999999 does not exist."
      rows the good create left behind: 0

POST complete_upload -> 201, body 1 byte, a single space
  t+0.3s, 2.6s, 5.9s, 11.2s, 21.4s   image = <site>/images/status/transient/thumbnail_pending.png
  t+41.7s                            image = a presigned URL
DELETE -> 204, empty body. GET the same id -> 404
```

**Teaches**
- There is no conditional write. `If-Match`, `If-Unmodified-Since` and `If-None-Match` are ignored and the
  update applies at 200, though a `GET` returns a weak `ETag`; echoing `updated_at` back is refused with
  `API update() Task.updated_at is editable on create only.` So a read-then-write guard narrows the race
  window and never closes it, and exactness needs serialisation outside the API (`recipes/005`).


| operation | the response returns | it omits | how to get the rest |
|---|---|---|---|
| `POST /entity/<type>` | the fields of the request body, the server-set ones (`created_at`, `updated_at`, `cached_display_name`), and every relationship as `{id, name, type}` | every field left at its default, and every dotted path | `GET /entity/<type>/{id}?fields=...` |
| `PUT /entity/<type>/{id}` | the whole record, changed fields and untouched ones alike | dotted paths only | the same follow-up `GET` |
| `PATCH /entity/<type>/{id}` | nothing: 404 with a null `detail` | everything | use `PUT` |
| batch `create` row | the same subset a single create returns | as a single create | one `GET` per created id |
| batch `update` row | the whole record, wrapped with `links` and `status` | dotted paths only | the same follow-up `GET` |
| batch `delete` row | `did_delete`, `id`, `uuid` | any field value | nothing to re-read |
| `_upload` `complete_upload` | 201 with a one-byte body | the stored path and the final URL | poll the field until it stops matching `/images/status/transient/` |
| `DELETE /entity/<type>/{id}` | 204, empty body | everything | the id answers 404 from then on |

- **Trap.** `?fields` on a write is accepted and ignored, plain names and dotted paths alike, with no error, the
  same quiet drop a bogus `?fields` name gets on a read (probe 004). The reported create-versus-update
  asymmetry is real but inverted: the create response is the thin one. Neither verb resolves
  `project.Project.name` or `entity.Shot.code`, and both return the link's own `name` under `relationships`,
  so a second call is needed only for a linked entity's other fields.
- On the probed site a Version create answers 9 attributes and 15 relationships and an update answers 52
  and 20. The counts are site-specific; the ratio is the rule. A create body of 3 extra fields answered 12
  attributes, so the create response is what you sent plus the server defaults, not a fixed list.
- **A batch endpoint does exist**, undocumented: `POST /entity/_batch`, and it takes plain
  `application/json`, not the vendor Content-Type `_search` requires (probe 004).

      {"requests": [{"request_type": "create", "entity": "Version", "data": {...}},
                    {"request_type": "update", "entity": "Version", "record_id": N, "data": {...}},
                    {"request_type": "delete", "entity": "Version", "record_id": N}]}

  `entity` is the singular schema name, not the URL slug; the id key is `record_id`, and `entity_id` is read
  as 0 and 404s. One failing row rolls the whole batch back: a good create paired with an update of id
  999999999 left 0 rows behind. The response is `data`, one row per request, in order.
- Transcoding is the only write whose result is not readable at all on return (probe 013). On the probed
  site a 16x16 PNG thumbnail stayed at `/images/status/transient/thumbnail_pending.png` past t+21s and
  resolved by t+42s, so poll on the path prefix and never on elapsed time.
- **Unsettled.** One team reports a newly created Version's linked-entity field reading back empty at the
  moment of its own creation event, and built a diagnostic to fail loudly on it. This repo has no event
  listener, so the claim is untested here and a negative result would prove nothing. Settling it needs a
  listener reading the entity from inside the event callback and comparing against a read a second later.
