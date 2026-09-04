---
endpoint: GET /entity/<type>/<id>/followers
coverage: measured
tags: [follow, user, paging, note]
scope: api
measured: sample project 1 of 1, sandbox project written
verdict: The HumanUsers watching one record, whole and unpaged, with `name` the only attribute. `links.self` is spelled `/entity/HumanUser/<id>`, singular and CamelCase.
---

# GET /entity/<type>/<id>/followers

**Params**

| part | value |
|---|---|
| `<type>` | snake_case plural, as on every other `/entity` path |
| `<id>` | record id |

No query parameters exist. No `fields`, no `page[]`, no `sort`.

**Sample requests**

```python
r = c.get("/entity/notes/340/followers")
```

```json
{
  "data": [
    {"id": 68, "type": "HumanUser", "attributes": {"name": "<user>"},
     "links": {"self": "/api/v1/entity/HumanUser/68"}},
    {"id": 18, "type": "HumanUser", "attributes": {"name": "<user>"},
     "links": {"self": "/api/v1/entity/HumanUser/18"}},
    {"id": 67, "type": "HumanUser", "attributes": {"name": "<user>"},
     "links": {"self": "/api/v1/entity/HumanUser/67"}}
  ]
}
```

A record nobody follows answers 200 with an empty list, never 404:

```python
r = c.get("/entity/shots/862/followers")
```

```json
{"data": []}
```

**Response codes**

| status | when |
|---|---|
| 200 | the followers, `[]` when there are none |
| 404 | `detail: "Couldn't find Note with id=999999999"` |

**Edge cases**

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

**Links**

- `endpoints/get_entity_human_users_id_following`
- `endpoints/post_entity_human_users_id_follow`
- `endpoints/put_entity_type_id_unfollow`
- `findings/043_attention`
