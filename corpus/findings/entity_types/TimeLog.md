---
tags: [entity-type, time-log, task, duration, create, entity-field, trap]
scope: api
measured: first sample project read, sandbox project written
summary: Hours logged against a Task by one person on one day.
verdict: A TimeLog create requires only `project`; `date` defaults to the server's today instead of failing, `entity` takes any type despite valid_types ['Task'], and a script may log for any HumanUser.
---

# TimeLog

**Type** Schema name `TimeLog`, REST path slug `time_logs`. Project-scoped: `project` is a stock `entity`
field with `valid_types: ['Project']`, and a create without it is refused. 12 fields in all.

| path | result |
|---|---|
| `GET /entity/time_logs` | 200 |
| `GET /entity/time_log`, `GET /entity/TimeLog` | 200, the same rows; `links.self` normalises to `/api/v1/entity/time_logs/<id>` |
| `GET /entity/timelogs`, `GET /entity/timelog`, `GET /entity/timesheet_entries` | 404 `Entity type 'timelogs' does not exist.` |

The listing is site-wide and every row is project-scoped: one unfiltered page of 200 returned rows from
three projects on the probed site. Scope a read with
`[["project", "is", {"type": "Project", "id": N}]]`.

**Identity** None. TimeLog has no `code`, no `name` and no `content`, and asking for one is a 400.
`description` is the text a human reads, and `cached_display_name` is a server-managed copy of it. Neither
is unique. Key on `id`, or on the triple (`entity`, `user`, `date`).

| filter | result |
|---|---|
| `["description", "is", ...]` | matches |
| `["code", "is", ...]` | 400 `API read() TimeLog.code doesn't exist.` |
| `["name", "is", ...]` | 400 `API read() TimeLog.name doesn't exist.` |

**Create** `project` alone. The schema flags only `id` as `mandatory`, so its flags predict nothing here
(probe 012). `duration`, `entity`, `user` and `date` are all optional, and a create without them returns a
row that reads `duration: 0`, `description: "New Time Log"` and today's date.

| body | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `duration` alone, `date` alone, `entity` alone | 400, the same title with the body echoed |
| `entity` + `duration` | 400, the same title; a Task does not imply its project |
| `project` alone | 201, `duration` 0, `date` today, `description` `"New Time Log"` |
| `project` + `duration` | 201 |
| `project` + `entity` + `duration` | 201 |
| `project` + `duration` + `date` | 201 |
| `project` as a bare integer | 400 `API create() TimeLog.project expected [Hash, ... NilClass] data type(s) but got Integer: <id>` |

**Date** `date` is a `date` field, `YYYY-MM-DD` (`field_types/date`). A create that omits it is not
refused: the server stamps its own current date. A `PUT` clears it.

| sent | result |
|---|---|
| key omitted from the `POST` | 201, `date` set to the server's today |
| `"2026-01-05"` | 200, stored as sent |
| `"2026-01-05T09:00:00Z"` | 400 `Invalid date format: 2026-01-05T09:00:00Z. Correct format is: 2011-01-21` |
| `"05/01/2026"` | 400, the same title |
| `""` and `null` on a `PUT` | 200, reads back `null` |

A row with `date: null` still counts toward `Task.time_logs_sum`. On the probed site 0 of 1012 TimeLogs
hold a null `date`, so the state exists over REST and nothing in the web app produces it: always send the
day you mean.

**Duration and the rollup** `duration` is minutes and there is no unit anywhere on the field; read
`hours_per_day` from `GET /preferences` to render (`field_types/duration`). `Task.time_logs_sum` is the
read-only sum of the `duration` of every TimeLog whose `entity` is that Task, recomputed on every write
(`entity_types/Task`). Adding logs of 60, 45 and 120 to a sandbox Task moved it from 150 to 210, 255
and 375; a delete and an edit followed with plain arithmetic. `time_vs_est` is `est_in_mins - time_logs_sum`
and goes negative when nothing is estimated.

**Links** No field anywhere in the 114 types of `/schema` names `TimeLog` specifically, so the direction is
always TimeLog to Task; 51 generic any-entity fields list it among 100+ `valid_types`
(`field_types/entity`).

| field | data type | editable | `valid_types` |
|---|---|---|---|
| `entity` | entity | yes | `['Task']` |
| `user` | entity | yes | `['HumanUser']` |
| `project` | entity | yes | `['Project']` |
| `created_by`, `updated_by` | entity | no | `['HumanUser', 'ApiUser']` |

`valid_types` on `entity` does not bind, matching `field_types/entity`: a Shot and a Project were both
accepted at 201 and read back as their own type. `user` is enforced.

| write | result |
|---|---|
| `user` = a HumanUser other than the authenticated script | 201; `user` is that person, `created_by` stays the `ApiUser` |
| `user` = an ApiUser | 400 `Invalid field value, update failed [5 - Update failed for [TimeLog.user]: HumanUser expected, got ApiUser]` |
| `user` = a Project | 400, the same title, `got Project` |
| `user` = a bare integer | 400 `API create() TimeLog.user expected [Hash, ... NilClass] data type(s) but got Integer: <id>` |
| `user` = `null` | 201, reads back `null` |
| `entity` = a Shot, `entity` = a Project | 201 each, stored as sent |

A tool can log on someone's behalf: set `user`, and `created_by` records the script that did it. `user` is
optional, and an omitted one is not filled in from the credentials. On the probed site 452 of 1012 TimeLogs
have no `user` at all, so filter `["user", "is_not", null]` before attributing time to anyone.

Both link fields take a `{type, id}` hash. A bare id is 400 on read as well as on write:
`API summarize() TimeLog.entity expected [Hash, ... NilClass] data type(s) but got Integer: <id>`.
Read the Task and the person in one call rather than a second fetch (probe 003):

```
POST /entity/time_logs/_search   Content-Type: application/vnd+shotgun.api3_array+json
{"filters": [["project", "is", {"type": "Project", "id": N}]],
 "fields": ["duration", "date", "entity.Task.content", "user.HumanUser.login"]}
 -> {"duration": 180, "date": "2026-01-30", "entity.Task.content": "<task>",
     "user.HumanUser.login": "<user>"}
```

**Status** None. TimeLog has no `status_list` and no `list` field.

**Traps**
- `date` never fails a create. Omit it and the row gets the server's current date, in the site's timezone,
  not the day the work happened. A backfill that forgets `date` silently lands on today.
- `entity` is not restricted to Task despite `valid_types: ['Task']`. A tool that logs against a Shot gets
  201 and a row no Task rollup will ever count. Check the type client-side.
- `Task.time_logs_sum` is read-only and 400s on a write (`entity_types/Task`). Change the sum by creating,
  editing or deleting a TimeLog.
- `created_by` and `created_at` are `editable on create only`: a `PUT` to either is 400
  `API update() TimeLog.created_by is editable on create only.` `user` stays editable for the row's life.
