---
tags: [follow, user, task, version, observe]
endpoints: [GET /entity/<type>/<id>/activity_stream, GET /entity/human_users/<user_id>/following]
phase: observe
scope: api
measured: sample project 1 of 1, and one HumanUser's own stream, site-wide
verdict: A HumanUser's activity_stream is what the person created, not what they follow: 0 of 9 rows touched the 81 followed records. A feed is a fan-out over their tasks' Shots and Assets.
---

# 066_user_feed

**Q** Is `/entity/human_users/<id>/activity_stream` the person's feed, or the changes to their own record?

**Endpoint** `GET /entity/<type>/<id>/activity_stream ; GET /entity/human_users/<user_id>/following`

**Docs claim** The site's `/spec.json` allows any entity type in the path and says nothing about what a
HumanUser stream holds.

**Actual**

```
GET /entity/human_users/<me>/activity_stream?limit=500 -> 200  updates=9  earliest_update_id=0
   update_type    {'create': 9}
   meta.type      {'new_entity': 9}
   primary_entity {'Version': 6, 'PublishedFile': 2, 'HumanUser': 1}
   created_by     {'me': 8, 'HumanUser': 1}       the ninth is the creation of the HumanUser row itself
GET /entity/human_users/<me>/following            -> 200  81 rows  {'Task': 77, 'Note': 4}
   of 9 updates: 8 made by the person, 0 on a record they follow, 1 about the HumanUser row

the same call with scope=sudo_as_login:<me>       -> 200  the same 9 rows, read: false on every one

a Task the person is assigned to, and the Shot it sits on
GET /entity/tasks/3788/activity_stream?limit=100  -> 200  updates=3   primary_entity {'Task': 3}
GET /entity/shots/880/activity_stream?limit=100   -> 200  updates=22  primary_entity {'Task': 19, 'Shot': 2, 'Version': 1}
GET /entity/tasks/3780/activity_stream?limit=100  -> 200  updates=4   primary_entity {'Task': 4}
GET /entity/shots/878/activity_stream?limit=100   -> 200  updates=21  primary_entity {'Task': 19, 'Shot': 1, 'Version': 1}

entity_fields[Version]=sg_status_list,entity on the HumanUser stream widens primary_entity:
   Version: ['entity', 'id', 'name', 'sg_status_list', 'status', 'type']
```

**Teaches**

- A HumanUser stream is the rows whose `created_by` is that person, plus the creation of the row
  itself. It is not the Inbox and it is not the follow list: the 77 Tasks and 4 Notes the person
  follows contributed nothing to it, and impersonating the person did not change it.
- A Shot's stream holds its Tasks and Versions as `primary_entity` rows; a Task's stream holds the
  Task alone. A feed of "my day" is one call per distinct Shot or Asset behind the person's Tasks,
  merged on `id` descending, with `max_id` for paging (`endpoints/get_entity_type_id_activity_stream`).
- `read` was false on every row under the script token and under `sudo_as_login`, so the stream does
  not expose the Inbox's read state. Keep the last `id` seen locally and page with `min_id`.
- What a Note or a Reply writes to any stream is `probe 067`.
