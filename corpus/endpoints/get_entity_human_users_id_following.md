---
endpoint: GET /entity/human_users/<user_id>/following
coverage: measured
tags: [follow, user, paging, project, cost]
scope: api
measured: sample project 1 of 1, sandbox project written
verdict: Everything one HumanUser follows, unpaged in a single body, filterable only by `entity` and `project_id`. An ApiUser id is a 404, so a script has no follow list of its own.
---

# GET /entity/human_users/<user_id>/following

**Params**

| part | value |
|---|---|
| `<user_id>` | a HumanUser id. Any other user type is a 404 |
| `entity` | one type to keep. `Note` and `notes` both work |
| `project_id` | keep only rows in that project |

No `fields`, no `page[]`, no `sort`.

**Sample requests**

```python
r = c.get("/entity/human_users/3/following")
```

```json
{
  "data": [
    {"id": 346, "type": "Note", "links": {"self": "/api/v1/entity/Note/346"}},
    {"id": 360, "type": "Note", "links": {"self": "/api/v1/entity/Note/360"}},
    {"id": 391, "type": "Note", "links": {"self": "/api/v1/entity/Note/391"}}
  ]
}
```

On the probed site that call answered 896 rows in one body, 707 `Note` and 189 `Task`, with no page
key. The two filters cut it server-side:

```python
c.get("/entity/human_users/3/following", params={"entity": "notes"})                 # 707 rows
c.get("/entity/human_users/3/following", params={"entity": "Note"})                  # 707 rows
c.get("/entity/human_users/3/following", params={"entity": "shots"})                 # 0 rows
c.get("/entity/human_users/3/following", params={"project_id": 70})                  # 865 rows
c.get("/entity/human_users/3/following", params={"entity": "notes", "project_id": 70})  # 707 rows
```

**Response codes**

| status | when |
|---|---|
| 200 | the list, `[]` when the user follows nothing matching |
| 400 | `source: {"entity": ["entity is not valid"]}` |
| 404 | `detail: "Couldn't find HumanUser with id=\"999999999\""` |
| 404 | `detail: "Couldn't find Project with id=\"999999999\""` for an unknown `project_id` |

**Edge cases**

- An ApiUser id under `/entity/human_users/` answers `Couldn't find HumanUser with id="1"`. A script
  token cannot ask what it follows, only what a named person follows.
- `entity` takes the schema name or the snake_case plural, unlike the `entity` key in the
  `follow` body, which takes the schema name alone and answers 500 to the plural.
- `links.self` is `/api/v1/entity/Note/346`, singular and CamelCase, matching
  `endpoints/get_entity_type_id_followers` and nothing else in the API. It resolves at 200.
- Each row is id, type and a link. Neither the name of the followed record nor the date the follow
  started is returned, so a display list costs one call per row or a `_search` on the ids.
- Nothing pages. Filter with `entity` and `project_id` or take the whole list.

**Links**

- `endpoints/get_entity_type_id_followers`
- `endpoints/post_entity_human_users_id_follow`
- `endpoints/put_entity_type_id_unfollow`
- `findings/043_attention`
