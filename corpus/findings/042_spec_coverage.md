---
tags: [schema, discovery, cost]
endpoints: [GET /spec.<format>]
phase: schema
scope: api
measured: site-wide, one fetch
verdict: `GET /spec.json` returns the deployment's own OpenAPI v3 document. It advertises 62 operations against the 23 this corpus covers, and it disagrees with the published documentation.
---

# 042_spec_coverage

**Q** Does the site publish its own endpoint list, and which of those endpoints does the corpus cover?

**Endpoint** `GET /spec.json ; GET /spec.yaml`

**Docs claim** The reference documents `GET /spec.{format}` and returns an example body whose `paths`
is `{}`. It does not say the live document differs from the reference itself.

**Actual**

```
GET /spec.json -> 200 application/json  191452 bytes
GET /spec.yaml -> 200 text/yaml         241068 bytes
GET /spec.xml  -> 406, empty body
GET /spec      -> 404

openapi 3.0.0   title 'Flow Production Tracking REST API '   version '1.x'
servers[0].url  <site>/api/v1.1          <- not /api/v1
44 paths, 62 operations

covered 21 of 62 by a card; 41 with no card, in eight families:
  webhook          10   hooks, deliveries, test_connection, redeliver
  upload           8    POST and PUT forms, multipart, multipart_abort
  follow/activity  7    activity_stream, followers, following, follow, unfollow, thread_contents
  one record       4    POST /entity/<type>/<id>, GET .../<field>, relationships, _update_last_accessed
  site facts       5    license_info, work_day_rules x2, user_subscriptions x2, preferences/update
  search           3    _text_search, hierarchy/_expand, hierarchy/_search
  exports          2    exports/page/<id>.<format>
  transcode        1    transcode/attachment_metadata/<id>

cards with no operation in the spec: PUT <links.upload>, POST <links.complete_upload>
```

**Teaches**

- The deployment answering your calls will hand you its own endpoint list. Reconstructing one from
  documentation is unnecessary and, here, wrong.
- **The spec and the published reference disagree.** The reference documents
  `PUT /entity/{entity}/{record_id}/_revive`, `POST .../_upload_complete`,
  `PATCH /schema/{entity}/fields/{field}` and `PATCH /preferences`. This site's spec has none of those
  spellings, and has `PUT /schema/<type>/fields/<field>` and `PUT /preferences/update` instead. Probe
  041 measured the `PUT` on a schema field working. Read the spec, not the reference.
- `servers[0].url` ends in `/api/v1.1`. Every recorded call in this corpus was made against `/api/v1`.
  Whether the two versions differ is unmeasured.
- The two upload steps with no operation in the spec are correct as they stand: `links.upload` is a
  presigned storage URL and is not a route on this API at all.
- 191KB is too large to hand an agent. `probes/042_spec_coverage.py` prints the difference between the
  spec and `corpus/endpoints/`, which is the only part that changes.
