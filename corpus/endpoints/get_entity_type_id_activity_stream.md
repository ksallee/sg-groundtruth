---
endpoint: GET /entity/<type>/<id>/activity_stream
tags: [follow, paging, user, async, trap]
scope: api
measured: sample project 1 of 1, sandbox project written
verdict: The feed the web application draws, paged by `max_id` and `min_id` rather than by `page[]`. A record id that is not there answers 500, not the 404 the spec advertises.
---

# GET /entity/<type>/<id>/activity_stream

What happened to one record, newest first. It is a separate store from `EventLogEntry`
(`findings/025_event_log`) with its own ids, its own paging keys and its own latency.

**Params**

| part | value |
|---|---|
| `<type>` | snake_case plural, as on every other `/entity` path |
| `<id>` | record id |
| `limit` | 1 to 500, default 25. Outside that range it is a 400 |
| `max_id` | exclusive ceiling. The page-down key |
| `min_id` | exclusive floor. The top-up key |
| `entity_fields[<Type>]` | comma-separated fields added to `primary_entity` when its `type` matches |

No `page[size]`, no `page[number]`, no `sort`, no `fields`.

**Sample requests**

```python
r = c.get("/entity/shots/862/activity_stream", params={"limit": 3})
```

```json
{
  "data": {
    "entity_type": "Shot",
    "entity_id": 862,
    "latest_update_id": 246800,
    "earliest_update_id": 220896,
    "updates": [
      {
        "id": 230874,
        "update_type": "update",
        "meta": {
          "type": "attribute_change",
          "attribute_name": "sg_status_list",
          "entity_type": "Shot",
          "entity_id": 862,
          "field_data_type": "status_list",
          "old_value": "fin",
          "new_value": "ip",
          "platform_id": null
        },
        "created_at": "2026-04-24T03:55:01Z",
        "read": false,
        "primary_entity": {"type": "Shot", "id": 862, "name": "<shot code>", "status": "ip"},
        "created_by": {"type": "ApiUser", "id": 34, "name": "<script>", "status": null, "image": null}
      }
    ]
  },
  "links": {"self": "/api/v1/entity/shots/862/activity_stream?limit=3"}
}
```

Widen `primary_entity` by the type it holds, not by the type in the path:

```python
r = c.get("/entity/shots/862/activity_stream",
          params={"limit": 1, "entity_fields[Shot]": "code,sg_status_list"})
```

```
primary_entity without: ['id', 'name', 'status', 'type']
primary_entity with:    ['code', 'id', 'name', 'sg_status_list', 'status', 'type']
created_by is unchanged: ['id', 'image', 'name', 'status', 'type']
```

Page down with `max_id`, taking the value from the previous answer's `earliest_update_id`:

```python
r = c.get("/entity/shots/862/activity_stream", params={"limit": 3, "max_id": 220897})
```

```
200  updates=3  latest_update_id=220896  earliest_update_id=23265  ids [220896, 220895, 23265]
```

**Response codes**

| status | when |
|---|---|
| 200 | the window, `updates` empty when there is nothing in it |
| 400 | `source: {"limit": ["limit must be less than or equal to 500"]}` |
| 400 | `source: {"limit": ["limit must be greater than 0"]}` for `0` and for a negative |
| 400 | `source: {"limit": ["limit must be an integer"]}` |
| 404 | `detail: "Entity type 'bogus_things' does not exist."` |
| 500 | `title: "Shotgun Server Error"` for a record id that is not there |

**Edge cases**

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

**Links**

- `endpoints/get_entity_notes_id_thread_contents`
- `endpoints/get_entity_type_id_followers`
- `endpoints/post_entity_type_search`
- `findings/043_attention`
- `findings/025_event_log`
