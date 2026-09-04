---
tags: [page, entity-field, multi-entity, attachment, cost, discovery, silent]
endpoints: [POST /entity/<type>/<id>, GET /entity/<type>/<id>/<field>, GET /entity/<type>/<id>/relationships/<related_field>, PUT /entity/projects/<id>/_update_last_accessed, GET /exports/page/<page_id>.<format>, GET /exports/page/<page_id>/<layout_name>.<format>]
phase: read
scope: api
measured: sample project 1 of 1, sandbox project written
verdict: POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.
---

# 048_one_record_beyond_crud

**Q** What else answers on one record besides `GET`, `PUT` and `DELETE`?

**Endpoint** `POST /entity/shots/{id} ; GET /entity/versions/{id}/{field} ; GET /entity/versions/{id}/relationships/{field} ; PUT /entity/projects/{id}/_update_last_accessed ; GET /exports/page/{id}.csv`

**Docs claim** The site's own `/spec.json` names all six. It calls the `POST` "Revive a record", the
field read "Read file field", and it gives `csv` as the only value of `<format>`.

**Actual**

```
GET /entity/versions/17055/<field>
  code, sg_status_list, id, entity, playlists -> 400 "Field Version.code is not an image or attachment."
  image -> 200 {"data": "<presigned URL>", "links": {...}}   empty -> 200 {"data": null}
  sg_uploaded_movie -> 200 data keys [content_type, id, link_type, name, type, url]
  entity.Shot.code -> 406 text/html 1 byte   sg_not_a_field -> 404 "Field 'Version.sg_not_a_field' does not exist."
  ?alt=original|thumbnail -> 302 to storage; followed: 200 image/jpeg 51730 bytes; empty field -> 404
  ?alt=original with Range: bytes=0-100 -> 206 image/jpeg, Content-Range: bytes 0-100/196291
  ?alt=nope -> 400 {"alt": ["alt must be one of: original, thumbnail"]}

GET /entity/versions/17055/relationships/<field>
  entity    -> 200 {"data": {"id": 1230, "name": "charA", "type": "Asset"}, "links": {"self": ...}}
  playlists -> 200 {"data": []}   code, image -> 400 "Field 'code' is not a relationship field"
  a 60-link multi_entity: page[size], page[number], fields and sort all ignored, 60 rows, no links.next
  same ids in the same order as ?fields; 3048 bytes against 3231, and 120 against 353 for one link

POST /entity/shots/7683
  ?revive=1, retired row -> 200 {"data": {"type": "Shot", "id": 7683}, "meta": {"did_revive": true}}
  ?revive=1, live row    -> 200 meta {"did_revive": false}
  1, true and yes accepted; 0 and false -> 400 {"revive": ["revive must be true"]}; none -> "revive is missing"
  a body alongside revive=1 -> 200, not applied     ?fields=code ignored     logs Shotgun_Shot_Revival

PUT /entity/projects/1180/_update_last_accessed
  {"user_id": 3} -> 200 {"data": {"type": "Project", "id": 1180}, "links": {...}}   {} -> 400 "user_id is missing"
  {"user_id": 999999999} -> 200, identical body   project 999999999 -> 400 code 104 "Api::Errors::CrudError"
  GET the same path -> 404 "Field 'Project._update_last_accessed' does not exist."; under shots -> 404 detail null
  last_accessed_by_current_user null before and after, 0 event_log_entries

GET /exports/page/3074.csv -> 422 text/csv "Export for Page id=3074 not available"; 3074/<view>.csv the same
  .json .xml .txt set Content-Type from the extension, same 422 body; no extension -> 404 code 103
  999999999.csv -> 422 "Trying to perform export for retired Page id=999999999"; abc.csv -> id=0; 52 pages over 27 page_type values: 52 x 422, 0 x 200
```

**Teaches**

| call | what it is | what a caller assumes |
|---|---|---|
| `POST /entity/<type>/<id>` | revive a retired row | an update, or a create with an id |
| `GET /entity/<type>/<id>/<field>` | one image or attachment field, with a download | any field, read cheaply |
| `GET .../relationships/<related_field>` | the link list, unwrapped | a paged sub-collection |
| `PUT /entity/projects/<id>/_update_last_accessed` | stamps a user's project history | something readable back |
| `GET /exports/page/<page_id>.<format>` | a saved page view as CSV | any page, any format |

- `POST` on a single record is `DELETE` run backwards. `?revive=1` is required, `revive` must be
  truthy (`0` and `false` are refused with `revive must be true`), and a JSON body is accepted and
  discarded, so a client reaching for it as a `PUT` alias gets a 400 telling it about a parameter it
  never sent. The row comes back with the field values it had when it was retired.
- The revive response is `{"data": {"type", "id"}, "links", "meta": {"did_revive"}}` and has no
  `attributes` key, less than any other write returns (probe 024). `did_revive` is `false` on a row
  that was already live, at 200, which is the only way to tell a revive from a no-op. `?fields` is
  ignored here as on every other write. On the probed site a successful revive logged one
  `Shotgun_Shot_Revival` event and a no-op logged none.
- **`/<field>` is not a cheap single-field read.** Every non-file field is a 400 naming the field:
  `Field Version.code is not an image or attachment.` A dotted path is a 406 with a one-byte body,
  because the last dotted segment is parsed as a format extension. Use `?fields=` on
  `GET /entity/<type>/<id>` for anything else.
- `?alt=original` and `?alt=thumbnail` turn the same path into a download: a 302 to the presigned
  storage URL, which a redirect-following client fetches as the bytes. `Range` is forwarded to
  storage and answers 206 with `Content-Range`, so a client can read a header off a large movie
  without pulling the file. `Range` without `alt` is ignored and the field hash comes back at 200.
- `relationships/<related_field>` returns the identical `data` a normal read puts under
  `relationships`, minus the `links.related` pointer, and it is not paged: a 60-link field answered
  all 60 rows with no `links.next`, and `page[size]`, `page[number]`, `fields` and `sort` were all
  accepted and ignored. It saves 233 bytes on a single entity link and 183 on 60 of them, so it is
  worth a call only when the link list is the whole request.
- `_update_last_accessed` answers 200 for a `user_id` that does not exist and returns the same
  `{data, links}` either way, so nothing in the response says whether it did anything. On the probed
  site `Project.last_accessed_by_current_user` read `null` before and after, and no `EventLogEntry`
  was written, because that field is relative to the requesting user and a script is not the user it
  stamps. There is no read-back over REST; treat the call as write-only.
- The path is fixed to `projects`. `PUT /entity/shots/<id>/_update_last_accessed` is a 404 with a null
  `detail`, and `GET` on the project path falls through to the file-field route and answers
  `Field 'Project._update_last_accessed' does not exist.`, which names a field nobody asked for.
- `<format>` is not validated. `.json`, `.xml` and `.txt` all answer, and the extension sets the
  response `Content-Type` while the body stays the same plain-text string. Drop the extension and the
  route stops matching: 404, code 103. Whether a successful export honours anything but `csv` is
  unmeasured, because nothing exported.
- **Export is off by default and there is no field that says so.** A page id that does not exist
  answers `Trying to perform export for retired Page id=999999999`, and a non-numeric id is read as
  `id=0`, so a 422 does not distinguish a missing page from a page whose view is not marked
  exportable. On the probed site 52 pages across all 27 `page_type` values answered 422 and none
  answered 200; `Page` has no `exportable` field and the flag is not in the layout `settings_json`
  probe 023 reads, so a client cannot discover which pages will work without trying each one.
