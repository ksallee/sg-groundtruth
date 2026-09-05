---
evidence: [findings/043_attention]
endpoints: [GET /entity/<type>/<id>/activity_stream, POST /entity/human_users/<user_id>/follow]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: sample project 1 of 1, sandbox project written
summary: A record id that does not exist on activity_stream is a 500, and the follow body answers 500 for the plural entity name every URL on the API uses while an invalid name answers 400.
---

# 009_attention_500s_on_bad_input

**Expected** A request naming a row that is not there is a 404, and a request naming an entity type the
server does not accept is a 400. The site's own `/spec.json` gives `activity_stream` a 404 for a record
that is not there.

**Actual**

| call | answer |
|---|---|
| `GET /entity/shots/999999999/activity_stream` | `500 Shotgun Server Error` |
| `GET /entity/bogus_things/1/activity_stream` | `404 Entity type 'bogus_things' does not exist.` |
| `POST .../follow` with `{"entities": [{"record_id": N, "entity": "shots"}]}` | `500 Shotgun Server Error` |
| `POST .../follow` with `{"entities": [{"record_id": N, "entity": "Bogus"}]}` | `400 {"entities": {"0": {"entity": ["entity is not valid"]}}}` |
| `POST .../follow` with `{"entities": [{"record_id": N, "entity": "Shot"}]}` | `204`, followed |

An unknown entity type is handled on both calls. A missing row and a plural entity name are not.

`shots` is the spelling every URL on this API uses, `/entity/shots/<id>`, so the value that 500s is the
one a caller reaches for first, and an outright invalid name gets the better error.

**Reproduce**

```
curl -sS -o /dev/null -w '%{http_code}\n' \
  "$SITE/api/v1/entity/shots/999999999/activity_stream" -H "Authorization: Bearer $TOKEN"
# 500

curl -sS -X POST "$SITE/api/v1/entity/human_users/<user_id>/follow" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"entities":[{"record_id":<id>,"entity":"shots"}]}'
# 500

curl -sS -X POST "$SITE/api/v1/entity/human_users/<user_id>/follow" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"entities":[{"record_id":<id>,"entity":"Bogus"}]}'
# 400, which is the answer the plural should get
```

**Impact** A 500 is retried by every client that retries anything, so a stale record id becomes repeated
load on the server rather than an error the caller handles. It also tells the caller nothing, so the
plural case reads as an outage rather than a bad request, and the difference between `shots` and `Shot`
is not something the response can teach.

**Proposed change** Answer 404 for a record id that does not exist, matching the site's own spec, and
400 for an entity value the endpoint does not accept, matching what an unknown name already gets on the
same call.
