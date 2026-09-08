---
endpoint: PUT /entity/projects/<id>/_update_last_accessed
coverage: measured
tags: [project, user, silent]
scope: api
measured: sandbox project written
verdict: Stamps one user's last visit to a project. Write-only: a `user_id` that does not exist answers the same 200, and nothing readable over REST changes.
---

# PUT /entity/projects/<id>/_update_last_accessed

The only entity-specific write on the API. `projects` is a literal path segment, not the usual
`<type>` slot.

**Params**

| part | value |
|---|---|
| `<id>` | a `Project` id |
| body | `{"user_id": N}`, required |
| `Content-Type` | `application/json` |

**Sample requests**

```python
c.put("/entity/projects/1180/_update_last_accessed", json={"user_id": 3}).json()
```

```json
{"data": {"type": "Project", "id": 1180},
 "links": {"self": "/api/v1/entity/projects/1180"}}
```

A user id that is not on the site answers the identical body at 200.

No `user_id`:

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
             "source": {"user_id": ["user_id is missing"]}}]}
```

A project id that is not there:

```json
{"errors": [{"status": 400, "code": 104, "title": "Api::Errors::CrudError",
             "source": null, "detail": null}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | accepted, whether or not the user exists |
| 400 | `source: {"user_id": ["user_id is missing"]}` |
| 400 | `Api::Errors::CrudError`, code 104, for a project id that is not there |
| 404 | the path under any other type, with a null `detail` |
| 404 | `GET` on this path: `Field 'Project._update_last_accessed' does not exist.` |

**Edge cases**

| you send | result |
|---|---|
| `{"user_id": 3}` | 200 |
| `{"user_id": "3"}` | 200, the string is accepted |
| `{"user_id": 999999999}` | 200, no error |
| `{}` | 400 `user_id is missing` |
| the path under `shots` | 404, `detail` null |

- `Project.last_accessed_by_current_user` is relative to the requesting account, and a script has no
  HumanUser row to be current, so a script reads `null` before and after its own call. It is not
  unreadable: a token acting as the stamped user reads the timestamp back. Measured on the probed
  site, a script `PUT` with `{"user_id": 24}` then read `null` as itself and
  `'2026-09-08T16:00:59Z'` through `scope=sudo_as_login:<that user>` (probe 027). The write logged no
  `EventLogEntry`. Fire and forget only if you have no way to be the user you stamped.
- A bad `user_id` is a silent 200. Validate the id against `GET /entity/human_users` first if it
  matters that the stamp landed.
- `GET` on the same path falls through to the file-field route, so the 404 names a field nobody asked
  for. The endpoint is `PUT` only.

**Links**

- `endpoints/get_entity_type_id_field`
- `endpoints/put_entity_type_id`
- `entity_types/Project`
