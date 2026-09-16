# Endpoints — Attention

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /entity/<type>/<id>/activity_stream`

The feed the web application draws, paged by `max_id` and `min_id` rather than by `page[]`. A record id that is not there answers 500, not the 404 the spec advertises.

`GET /entity/shots/999999999/activity_stream` answers 500 with the generic support message, not the
404 the site's own `/spec.json` advertises. The same 500 came back on `notes`, `projects` and
`versions`, so check the record exists before asking for its stream.

The two id keys bound the window that was searched, not the record's own history:

| call | `latest_update_id` | `earliest_update_id` |
|---|---|---|
| no parameters | `246800`, the newest id on the site | `456`, the lowest id returned |
| `limit=500` | `246800` | `0`, the stream ran out |
| `max_id=220897` | `220896`, one below `max_id` | `23265`, the lowest id returned |
| `min_id=220897` | `246800` | `220898`, one above `min_id` |

- Page down by passing the previous `earliest_update_id` back as `max_id`. Both bounds are
  exclusive, so nothing repeats. Stop on `earliest_update_id: 0`.

- `latest_update_id` is site-wide with no `max_id`: a Shot whose own newest update is `230874` still
  reported `246800`, and the same number came back on a Project in the same run.

- `entity_fields` is keyed by the type of `primary_entity`, so a mixed stream needs one key per type
  it can hold. It does not widen `created_by`.

- `read` is per-viewer and was `false` on every update a script token read.

**Measured by**

- `043_attention` (findings) — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.  
  rules: `doors/findings-observe`
- `066_user_feed` (findings) — A HumanUser's activity_stream is what the person created, not what they follow: 0 of 9 rows touched the 81 followed records. A feed is a fan-out over their tasks' Shots and Assets.  
  rules: `doors/findings-observe`
- `067_notes_in_the_stream` (findings) — A Reply reaches every linked stream in 33 s as `create_reply`, creates too; a script's Note create and status changes were absent after 430 s. Write as a person.  
  rules: `doors/findings-observe`
- `009_attention_500s_on_bad_input` (reports) — A record id that does not exist on activity_stream is a 500, and the follow body answers 500 for the plural entity name every URL on the API uses while an invalid name answers 400.  
  rules: `doors/reports`

**Silent on this call**

- `043_attention` — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.
- `067_notes_in_the_stream` — A Reply reaches every linked stream in 33 s as `create_reply`, creates too; a script's Note create and status changes were absent after 430 s. Write as a person.

`corpus/endpoints/get_entity_type_id_activity_stream.md`

## `GET /entity/<type>/<id>/followers`

The HumanUsers watching one record, whole and unpaged, with `name` the only attribute. `links.self` is spelled `/entity/HumanUser/<id>`, singular and CamelCase.

- `links.self` is `/api/v1/entity/HumanUser/68`, singular and CamelCase, where every other
  `links.self` in the API is `/entity/human_users/68`. The path resolves at 200 either way, so a
  client that follows the link works and a client that parses the type segment out of it breaks.

- `name` is the only attribute. Anything else about the user costs a second call.

- The list is not ordered by id. On the probed site, the most-followed of twenty Notes answered
  `[68, 18, 67, 17, 19]`.

- There is no paging key and no cap parameter, so a widely followed record returns every follower in
  one body.

- On the probed site every follower of every record was a `HumanUser`, and a Project answered `[]`
  even though the web application offers a project follow.

**Measured by**

- `043_attention` (findings) — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.  
  rules: `doors/findings-observe`

**Silent on this call**

- `043_attention` — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.

`corpus/endpoints/get_entity_type_id_followers.md`

## `PUT /entity/<type>/<id>/unfollow`

Removes one named user from one record at 204, and answers 204 again when that user was never following. It is PUT on the record, the mirror image of the POST on the user that follows.

| sent | result |
|---|---|
| `PUT`, `{"user_id": 3}`, user follows | 204, follower removed |
| `PUT`, `{"user_id": 3}`, user does not follow | 204, nothing changed |
| `PUT`, `{}` | 400 `user_id is missing` |
| `PUT`, `{"user_id": 999999999}` | 404 `Couldn't find HumanUser with id=999999999` |
| `POST`, `{"user_id": 3}` | 404 with `detail: null` |

- 204 says nothing about whether a follow was there to remove. Read `followers` first if you need to
  know, or accept it as idempotent.

- The method matters. `POST` on the same path answers a 404 whose `detail` is `null`, which reads
  like a missing record rather than a wrong verb.

- The pair is asymmetric: `POST /entity/human_users/<user_id>/follow` puts the user in the path and
  many records in the body, this puts one record in the path and one user in the body. A wrapper
  taking `(user, records)` has to unroll the loop for the unfollow half.

- The record id is not validated separately from the type, and a missing HumanUser is what 404s.

**Measured by**

- `043_attention` (findings) — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.  
  rules: `doors/findings-observe`

**Silent on this call**

- `put_entity_type_id_unfollow` — Removes one named user from one record at 204, and answers 204 again when that user was never following. It is PUT on the record, the mirror image of the POST on the user that follows.
- `043_attention` — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.

`corpus/endpoints/put_entity_type_id_unfollow.md`

## `POST /entity/human_users/<user_id>/follow`

Subscribes one HumanUser to a list of records at 204. `entity` must be the CamelCase schema name: the snake_case plural every path uses answers 500, and a bad id in the list 404s after applying the good ones.

| sent | result |
|---|---|
| `{"entities": [{"record_id": 7668, "entity": "Shot"}]}` | 204, followed |
| the same call again | 204, still one follower |
| `{"entities": [{"record_id": 7669, "entity": "shots"}]}` | 500, not followed |
| `{"record_id": 7668, "entity": "Shot"}` | 400 `entities is missing` |
| `{}` | 400 `entities is missing` |
| `{"entities": []}` | 204, nothing followed |
| one good record and one missing id | 404, and the good one is followed |

- **The call is not atomic.** A list holding a live id and a missing one answers
  `404 Couldn't find Shot with id=999999999`, and reading the live record back shows the follow was
  applied. A 404 here does not mean nothing happened, so re-read `followers` rather than retrying
  the whole list.

- The 415 body is the same one `/hierarchy/_expand` returns (`findings/046_search_without_a_path`):
  a client that sets `application/vnd+shotgun.api3_array+json` for every POST fails on this one.

- 204 has no body, so nothing names which entries were applied.

- The user is in the path and the records are in the body. Unfollowing inverts that: see
  `endpoints/put_entity_type_id_unfollow`.

**Measured by**

- `043_attention` (findings) — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.  
  rules: `doors/findings-observe`
- `009_attention_500s_on_bad_input` (reports) — A record id that does not exist on activity_stream is a 500, and the follow body answers 500 for the plural entity name every URL on the API uses while an invalid name answers 400.  
  rules: `doors/reports`

**Silent on this call**

- `post_entity_human_users_id_follow` — Subscribes one HumanUser to a list of records at 204. `entity` must be the CamelCase schema name: the snake_case plural every path uses answers 500, and a bad id in the list 404s after applying the good ones.
- `043_attention` — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.

`corpus/endpoints/post_entity_human_users_id_follow.md`

## `GET /entity/human_users/<user_id>/following`

Everything one HumanUser follows, unpaged in a single body, filterable only by `entity` and `project_id`. An ApiUser id is a 404, so a script has no follow list of its own.

- An ApiUser id under `/entity/human_users/` answers `Couldn't find HumanUser with id="1"`. A script
  token cannot ask what it follows, only what a named person follows.

- `entity` takes the schema name or the snake_case plural, unlike the `entity` key in the
  `follow` body, which takes the schema name alone and answers 500 to the plural.

- `links.self` is `/api/v1/entity/Note/346`, singular and CamelCase, matching
  `endpoints/get_entity_type_id_followers` and nothing else in the API. It resolves at 200.

- Each row is id, type and a link. Neither the name of the followed record nor the date the follow
  started is returned, so a display list costs one call per row or a `_search` on the ids.

- Nothing pages. Filter with `entity` and `project_id` or take the whole list.

**Measured by**

- `043_attention` (findings) — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.  
  rules: `doors/findings-observe`
- `066_user_feed` (findings) — A HumanUser's activity_stream is what the person created, not what they follow: 0 of 9 rows touched the 81 followed records. A feed is a fan-out over their tasks' Shots and Assets.  
  rules: `doors/findings-observe`

**Silent on this call**

- `043_attention` — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.

`corpus/endpoints/get_entity_human_users_id_following.md`

## `GET /entity/notes/<id>/thread_contents`

A Note, its Attachments and its Replies as one flat list in time order. The Note and the Attachments name their author under `created_by`, a Reply names it under `user`.

The author key changes with the row type, and so does what `entity_fields` can add:

| row type | author under | `entity_fields` widened it |
|---|---|---|
| `Note` | `created_by` | yes |
| `Attachment` | `created_by` | yes |
| `Reply` | `user` | no |

- A Reply's `user` hash has a fourth key, `image`, a presigned avatar URL re-signed per read. The
  `created_by` hash on the other two rows has no `image`.

- `entity_fields[Reply]` was accepted and changed nothing, so extra Reply fields need a
  `POST /entity/replies/_search`.

- `content` is absent from an Attachment row. Only its id, type, timestamp and author are returned
  unless `entity_fields[Attachment]` asks for more.

- A Note with no replies answers one row, its own, at 200.

- The 404 for another type is worded as a missing field rather than a missing route, which is what
  distinguishes it from a bad id.

**Measured by**

- `043_attention` (findings) — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.  
  rules: `doors/findings-observe`

**Silent on this call**

- `043_attention` — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.

`corpus/endpoints/get_entity_notes_id_thread_contents.md`
