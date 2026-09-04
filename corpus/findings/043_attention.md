---
tags: [follow, user, note, reply, paging, header, async, trap, silent]
endpoints: [GET /entity/<type>/<id>/activity_stream, GET /entity/<type>/<id>/followers, GET /entity/human_users/<user_id>/following, POST /entity/human_users/<user_id>/follow, PUT /entity/<type>/<id>/unfollow, GET /entity/notes/<id>/thread_contents]
phase: observe
scope: api
measured: sample project 1 of 1, sandbox project written
verdict: The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.
---

# 043_attention

**Q** How does the API expose attention: who is following what, and what changed on a record?

**Endpoint** `GET /entity/<type>/<id>/activity_stream ; GET /entity/<type>/<id>/followers ; GET /entity/human_users/<user_id>/following ; POST /entity/human_users/<user_id>/follow ; PUT /entity/<type>/<id>/unfollow ; GET /entity/notes/<id>/thread_contents`

**Docs claim** The site's own `/spec.json` lists all six, gives `activity_stream` a 404 for a record
that is not there, and types the follow body's `entity` as `"Task"` without saying the plural is
refused.

**Actual**

```
=== activity_stream pages on its own keys, and 500s on a missing record
GET /entity/shots/862/activity_stream            -> 200  25 updates  lat 246800  ear 456
GET .../activity_stream?limit=500                -> 200  25 updates  lat 246800  ear 0
GET .../activity_stream?limit=501                -> 400 limit must be less than or equal to 500
GET .../activity_stream?limit=3&max_id=220897    -> 200  ids [220896, 220895, 23265]  lat 220896
GET .../activity_stream?limit=50&min_id=220897   -> 200  ids [230874]                 ear 220898
GET /entity/shots/999999999/activity_stream      -> 500 Shotgun Server Error
GET /entity/bogus_things/1/activity_stream       -> 404 Entity type 'bogus_things' does not exist.

=== follow takes the schema name; the plural every path uses is a 500
{"entities": [{"record_id": 7668, "entity": "Shot"}]}   -> 204, followed
{"entities": [{"record_id": 7669, "entity": "shots"}]}  -> 500 Shotgun Server Error
{"entities": [{"record_id": 7668, "entity": "Bogus"}]}  -> 400 {"entities": {"0": {"entity": ["entity is not valid"]}}}
{"record_id": 7668, "entity": "Shot"}                   -> 400 {"entities": ["entities is missing"]}
{"entities": []}                                        -> 204, nothing followed
Content-Type: application/vnd+shotgun.api3_array+json   -> 415 Content-Type must be one of: 'application/json'.
one live id and one missing id in the same list         -> 404 Couldn't find Shot with id=999999999
  and GET /entity/shots/<live>/followers then shows the follow applied

=== the same word, three vocabularies
POST .../follow      body `entity`: "Shot" only
GET  .../following   query `entity`: "Note" and "notes" both 200
every path segment:  "shots", "human_users", "notes"
links.self on both follower lists: /api/v1/entity/HumanUser/68  /api/v1/entity/Note/346

=== thread_contents flattens three types, and names the author twice
Note        ['content', 'created_at', 'created_by', 'id', 'type']
Attachment  ['created_at', 'created_by', 'id', 'type']
Reply       ['content', 'created_at', 'id', 'type', 'user']
GET /entity/versions/1/thread_contents -> 404 Field 'Version.thread_contents' does not exist.
```

**Teaches**

- **`activity_stream` is not the event log.** It has its own id space, its own paging keys and its
  own latency. On the probed site the newest update was id `246800` dated two days before the run,
  and three Shots created during the run were absent from their own streams and from the project's
  after 90 seconds of polling. Read `EventLogEntry` (`probe 025`) for anything a write has to
  confirm.
- Page it with `max_id`, not `page[]`. Both bounds are exclusive, `earliest_update_id` is the floor
  reached, and `0` there means the stream ran out. `latest_update_id` is site-wide when no `max_id`
  is given, so it does not describe the record you asked about.
- A record id that is not there answers 500 on `activity_stream`, on all four types tried, where
  `followers`, `following` and `thread_contents` all answer a named 404. Check the record first.
- The follow body's `entity` is the CamelCase schema name and nothing else. `"shots"`, correct in
  every path segment and accepted by `following?entity=`, is a 500 with no clue in it.
- **A partial follow list applies its good half and returns 404.** The 404 names only the missing
  id, so treat the call as non-atomic and re-read `followers`.
- Neither follower list pages or takes `fields`. On the probed site one user's `following` was 896
  rows in a single body, each row id, type and a link, with no name and no follow date.
- `thread_contents` returns Note, Attachment and Reply interleaved by time. The Note and Attachment
  rows name their author under `created_by`, the Reply rows under `user`, and `entity_fields`
  widened the first two and was ignored on the third.
