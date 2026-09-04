---
endpoint: POST /entity/human_users/<user_id>/follow
tags: [follow, user, header, error-handling, silent, trap]
scope: api
measured: sandbox project written
verdict: Subscribes one HumanUser to a list of records at 204. `entity` must be the CamelCase schema name: the snake_case plural every path uses answers 500, and a bad id in the list 404s after applying the good ones.
---

# POST /entity/human_users/<user_id>/follow

**Params**

| part | value |
|---|---|
| `<user_id>` | a HumanUser id. Any other user type is a 404 |
| `Content-Type` | `application/json`. A vendor type is a 415 |
| `entities` | required list of `{"record_id": <int>, "entity": "<SchemaName>"}` |
| `entities[].entity` | the CamelCase schema name, `Shot`, never `shots` |

**Sample requests**

```python
r = c.post("/entity/human_users/3/follow",
           json={"entities": [{"record_id": 7668, "entity": "Shot"}]})
```

```
204, empty body
```

```python
r = c.get("/entity/shots/7668/followers")
```

```json
{"data": [{"id": 3, "type": "HumanUser", "attributes": {"name": "<user>"},
           "links": {"self": "/api/v1/entity/HumanUser/3"}}]}
```

The plural spelling that works in every path segment does not work here:

```python
r = c.post("/entity/human_users/3/follow",
           json={"entities": [{"record_id": 7669, "entity": "shots"}]})
```

```json
{"errors": [{"status": 500, "code": 100, "title": "Shotgun Server Error", "source": null,
  "detail": "Please contact your Shotgun administrator, or contact Shotgun support at: ...
   Please pass on the following information so we can trace what happened: Request: ... Event: ..."}]}
```

A name that is not a schema name at all is a clean 400 that points at the offending index:

```python
r = c.post("/entity/human_users/3/follow",
           json={"entities": [{"record_id": 7668, "entity": "Bogus"}]})
```

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"entities": {"0": {"entity": ["entity is not valid"]}}}}]}
```

**Response codes**

| status | when |
|---|---|
| 204 | followed, including a repeat and an empty `entities` list |
| 400 | `source: {"entities": ["entities is missing"]}` |
| 400 | `source: {"entities": {"0": {"entity": ["entity is not valid"]}}}` |
| 404 | `detail: "Couldn't find Shot with id=999999999"` |
| 404 | `detail: "Couldn't find HumanUser with id=\"999999999\""` |
| 415 | `source: {"content_type": "Content-Type must be one of: 'application/json'."}` |
| 500 | `entity` given as the snake_case plural |

**Edge cases**

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

**Links**

- `endpoints/put_entity_type_id_unfollow`
- `endpoints/get_entity_type_id_followers`
- `endpoints/get_entity_human_users_id_following`
- `findings/043_attention`
