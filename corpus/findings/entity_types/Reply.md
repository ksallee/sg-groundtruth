---
tags: [entity-type, reply, note, create, entity-field, query, filter, trap]
scope: api
measured: first sample project read, sandbox project written
summary: One message in a thread, hanging off almost any row and not only off a Note.
verdict: Reply is site-wide with no project field, and entity accepts almost every type on the site, not only Note; send entity on create, because a Reply whose entity is null cannot be deleted.
---

# Reply

**Type** Schema name `Reply`, REST path slug `replies`. Both the English plural and the naive one resolve,
along with the singular and the schema name, so a client that guessed wrong still works.

| path | result |
|---|---|
| `GET /entity/replies` | 200; `links.self` normalises to `/api/v1/entity/replies/<id>` |
| `GET /entity/replys`, `GET /entity/Replies` | 200, the same rows |
| `GET /entity/reply`, `GET /entity/Reply` | 200, the same rows |
| `GET /entity/repliess` | 404 `Entity type 'repliess' does not exist.` |

Site-wide: seven fields, none of them `project`. A Reply takes its project from whatever its `entity`
points at, and there is no way to ask for one project's replies directly.

| project scope attempted | result |
|---|---|
| `_search` `[["project", "is", {"type": "Project", "id": N}]]` | 400 code 103 `API read() Reply.project doesn't exist.` |
| `GET ?filter[project]=N` | 400, same title, `source` `{"Reply.project": " does not exist. …"}` |
| `GET ?project_id=N` | 200, accepted and ignored |
| `POST /entity/replies` with a `project` key | 400 `API create() Reply.project doesn't exist.` |

**Identity** `content`, display name `Reply Text`, `data_type: text`. It is the body and the whole of the
row a human reads; there is no subject, title or code. Nothing is flagged `unique`, and `content` is the
only field flagged `mandatory`, which the create contract below contradicts. `cached_display_name` is
filled from `content` at create time and is what a `Note.replies` link returns as its `name`.

**Create** `POST /entity/replies`, `Content-Type: application/json`. No field is required.

| body sent | result |
|---|---|
| `{}` | 201, `content` null, `entity` null, `publish_status` `"published"` |
| `{"project": {"type": "Project", "id": N}}` | 400 `API create() Reply.project doesn't exist.` |
| `{"content": "…"}` | 201, orphaned: `entity` null |
| `{"entity": {"type": "Note", "id": N}}` | 201, linked, `content` null |
| `{"entity": {"type": "Note", "id": N}, "content": "…"}` | 201, the usable call |
| `{"entity": {"type": "Version", "id": N}, "content": "…"}` | 201, linked to the Version |
| `{"entity": N, "content": "…"}` | 400 `API create() Reply.entity expected [Hash, ActiveSupport::HashWithIndifferentAccess, … NilClass] data type(s) but got Integer: N` |

`publish_status` is a plain `text` field the server sets to `published`; it is editable and is not a
`list`, so it has no vocabulary to validate against. A `PUT` afterwards changes `content`, clears it with
`null`, and repoints `entity` at a different type, all at 200.

**Links** Two entity fields and no multi_entity field. Both are written as a `{type, id}` hash under
`relationships` (`field_types/entity`).

| field | data type | `valid_types` | editable |
|---|---|---|---|
| `entity` | entity | every type on the site bar one | yes |
| `user` | entity | `['HumanUser', 'ApiUser', 'ClientUser']` | yes |

`Reply.entity` is a generic any-entity link, not a Note link. On the probed site it names 113 of the 114
types in `/schema`, the exception being one connection type. `Note`, `Delivery`, `Version` and `Reply`
itself are all in the list, and a create against `Note`, `Version` and `Delivery` each answered 201: a
Reply hung off a `Delivery` is as legal as one hung off a `Note`, and the external claim that replies
appear on Deliveries is what the schema says. Read `valid_types` for the set; it is site configuration.

Exactly two fields anywhere in `/schema` have `valid_types` of `['Reply']`, and both are `multi_entity`
and editable:

| field | holds |
|---|---|
| `Note.replies` | the Note's thread |
| `Delivery.replies` | the Delivery's thread |

Every other type takes replies through `Reply.entity` with no reverse field to read them back from, so for
those a client filters Reply instead:

```
POST /entity/replies/_search   Content-Type: application/vnd+shotgun.api3_array+json
{"filters": [["entity", "is", {"type": "Version", "id": <id>}]],
 "fields": ["content", "created_at", "user"], "sort": ["id"]}
```

**Order** Replies are returned oldest first and there is no ordering field of their own.

| read | order |
|---|---|
| `_search` with no `sort` | id ascending, which matched `created_at` ascending on every row measured |
| `sort: ["id"]`, `sort: ["created_at"]` | the same order |
| `sort: ["-id"]`, `sort: ["-created_at"]` | reversed |
| `Note.replies` on a `GET` of the Note | the same order as `sort: ["id"]` |

Sort on `id`, not on `created_at`. `created_at` has one-second resolution, and three replies posted inside
one second all read the same timestamp, leaving their order undefined.

**Status** None. Reply has no `status_list` and no `list` field. `publish_status` is text, not a status.

**Traps**
- **A Reply whose `entity` is null cannot be deleted.** `DELETE /entity/replies/<id>` answers 400 code 104
  `Delete failed for [Reply with id=N]: undefined method 'reflect_on_association' for class NilClass`.
  Assign any `entity` with a `PUT` and the same delete answers 204. A create that omitted `entity` is
  therefore permanent litter until it is repaired, so send `entity` in the create body.
- `content` is flagged `mandatory` and an empty body still answers 201, the same inversion probe 012 found
  on Version. The flag is not the contract.
- A filter for a type that is not in `Reply.entity`'s `valid_types` 400s with `API read()
  invalid/missing entity hash string 'type'`, even when live rows point at it. On the probed site the
  oldest replies hang off `Ticket`, a type absent from `/schema`, and the 400's own `Valid entity types`
  list names `Ticket` while the filter is refused. `[["entity", "type_is", "Ticket"]]` returns those rows
  at 200; use `type_is` for a type-level cut and reserve the hash for a type you read out of `valid_types`.
- `entity` is editable after the fact, with no type check against the original. A `PUT` moves a Reply from
  a Note to a Version at 200 and the Note's thread silently loses a row.
