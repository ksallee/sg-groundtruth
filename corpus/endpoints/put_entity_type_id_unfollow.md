---
endpoint: PUT /entity/<type>/<id>/unfollow
tags: [follow, user, silent, error-handling]
scope: api
measured: sandbox project written
verdict: Removes one named user from one record at 204, and answers 204 again when that user was never following. It is PUT on the record, the mirror image of the POST on the user that follows.
---

# PUT /entity/<type>/<id>/unfollow

**Params**

| part | value |
|---|---|
| `<type>` | snake_case plural, as on every other `/entity` path |
| `<id>` | record id |
| `Content-Type` | `application/json` |
| `user_id` | required integer, the HumanUser to remove |

One user, one record, per call. There is no list form and no way to clear every follower.

**Sample requests**

```python
r = c.put("/entity/shots/7668/unfollow", json={"user_id": 3})
```

```
204, empty body
```

```python
r = c.get("/entity/shots/7668/followers")
```

```json
{"data": []}
```

Omitting the key names it:

```python
r = c.put("/entity/shots/7668/unfollow", json={})
```

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"user_id": ["user_id is missing"]}, "detail": null, "meta": null}]}
```

**Response codes**

| status | when |
|---|---|
| 204 | removed, and also when the user was not following |
| 400 | `source: {"user_id": ["user_id is missing"]}` |
| 404 | `detail: "Couldn't find HumanUser with id=999999999"` |
| 404 | `detail: null` for `POST` on the same path |

**Edge cases**

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

**Links**

- `endpoints/post_entity_human_users_id_follow`
- `endpoints/get_entity_type_id_followers`
- `endpoints/get_entity_human_users_id_following`
- `findings/043_attention`
