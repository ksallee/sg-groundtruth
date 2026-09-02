---
tags: [write, version, create, entity-field]
scope: api
verdict: POST a Version with project as a {type, id} hash plus code; entity links take the same hash - a bare id 400s, and omitting project 400s even though only code is schema-mandatory.
---

# 012_create_version

**Q** What does creating a Version require, and how are entity links written on create?

**Endpoint** `POST /api/v1/entity/versions ; POST /api/v1/entity/shots ; GET /schema/Version/fields`

**Docs claim** Versions need a project; entity links are written as `{type, id}`.

**Actual**

```
sandbox project id: 1180
Version mandatory fields: ['code']
POST /entity/shots -> 201
shot id: 7444
  201 minimal (project + code): id=26262 rels=['created_by', 'cuts', 'notes', 'open_notes', 'playlists', 'project', 'published_files', 'sg_deliveries', 'tags', 'tasks', 'updated_by', 'user']
  201 with entity link: id=26263 rels=['created_by', 'cuts', 'entity', 'notes', 'open_notes', 'playlists', 'project', 'published_files', 'sg_deliveries', 'tags', 'tasks', 'updated_by', 'user']
  400 entity as bare id (no type): null
  400 no project at all: null
```

**Teaches**
- **Trap.** `/schema/Version/fields` marks only `code` mandatory, yet a body without `project` 400s. The
  schema's mandatory flags are not the create contract; `project` is required by the server regardless.
- An entity link is a hash: `"entity": {"type": "Shot", "id": N}` creates, `"entity": <id>` 400s.
  `project` takes the identical shape, and reads return both under `relationships` (probe 004).
- The 201 `relationships` block lists slots that were never set (`cuts`, `playlists`, `tags`), so its keys
  are not a record of your input. `entity` appears only when it was written, the one usable confirmation.
- Both 400s recorded as `null`: the probe captured `errors[0].detail` and these errors have none. The
  status codes are verified; the message text is `<unverified>`.
