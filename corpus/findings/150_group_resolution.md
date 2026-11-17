---
tags: [group, task, user, follow, dotted-field, permission]
endpoints: [POST /entity/<type>, GET /entity/<type>, GET /entity/<type>/<id>, PUT /entity/<type>/<id>, POST /entity/<type>/_search, GET /entity/<type>/<id>/followers]
phase: filter
scope: api
measured: sandbox project written, 2026-11-17; one Group of two Artists, a Shot and two Tasks, deleted; script and Artist
verdict: `task_assignees is <person>` misses a Task assigned to their Group; filter `task_assignees.Group.users`. Group assignment makes the members followers once, and an Artist reads Groups and members.
---

# 150_group_resolution

**Q** Do `Group.users` and a Group in `Task.task_assignees` resolve to the members, and what can an
Artist read of them?

**Endpoint** `POST /entity/groups ; GET /entity/groups ; POST /entity/tasks/_search ; GET /entity/tasks/<id>/followers`

**Docs claim** Silent. `Task.task_assignees` declares `valid_types: ['Group', 'HumanUser']`. Probe 027
found every Group on the probed site empty.

**Actual**

```
POST /entity/groups {"code": ..., "users": [B, C]}             -> 201
POST /entity/tasks task_assignees [the group]                 -> 201; reads back [Group], not the members
GET /entity/groups/<g>?fields=users                           -> [B, C]; sg_people []
GET /entity/human_users/<B>?fields=groups                     -> [the group]

filters on Tasks, sandbox project            task to the group   task to B   other Tasks
  task_assignees is B                        no                  yes         45
  task_assignees is the group                yes                 no          0
  task_assignees.Group.users is B            yes                 no          0
  task_assignees.HumanUser.groups is the group  no               yes         82
  task_assignees in [B, C]                   no                  yes         82

GET /entity/tasks/<task to the group>/followers -> [B, C]
GET /entity/tasks/<task to B>/followers         -> [B]

as B, an Artist (sudo_as_login): every read above returns the same rows and the same links;
  GET /entity/groups 200, 5 rows; GET /entity/human_users/<C> 200

PUT the group's users to [B]                        -> 200
  task_assignees.Group.users is C                   -> no Task
  followers of the task to the group                -> [B, C]   C still follows
PUT task_assignees += the operator                  -> followers [C, B, operator]
```

**People behind a Task's assignees**

| want | read or filter |
|---|---|
| the assignees as stored | `task_assignees`: HumanUsers and Groups, unexpanded |
| a Group's members now | `GET /entity/groups/<id>?fields=users` |
| Tasks assigned to a person directly | `["task_assignees", "is", <HumanUser>]` |
| Tasks assigned to a Group the person is in | `["task_assignees.Group.users", "is", <HumanUser>]` |
| both | the two filters in one `{"logical_operator": "or", "conditions": [...]}` (probe 030) |

**Teaches**
- A Group assignee is stored as the Group. `task_assignees is <person>` and `in [...]` match only
  direct assignments, and `task_assignees.HumanUser.groups` walks the human assignees' groups, not the
  group assignees. Expand a Group with `Group.users` before addressing anyone.
- Assigning a Group adds its members as followers at that moment. Removing a member later leaves them
  following, so the follower list drifts from the Group.
- On the probed site an Artist reads every Group, its `users`, and other people's rows, so an app
  signed in as an Artist can expand assignees itself. `sg_people` is the site's own field and was empty.
