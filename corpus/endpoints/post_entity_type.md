---
endpoint: POST /entity/<type>
tags: [write, create, entity-field, silent]
scope: api
measured: sandbox project written
verdict: `project` is the requirement on every project-scoped type and the identity field is not, whatever the schema says. `?fields` is ignored, and the 201 returns the whole record.
---

# POST /entity/<type>

**Params**

| part | value |
|---|---|
| body | the attributes, flat. An entity link is `{"type": "Shot", "id": 7650}` |
| `project` | required on every project-scoped type |
| `?fields` | accepted and ignored |

**Sample requests**

Nothing but a project, which is the whole contract:

```python
r = c.post("/entity/shots", json={"project": {"type": "Project", "id": 1180}})
```

The whole record, 2348 bytes:

```json
{
  "data": {
    "type": "Shot",
    "attributes": {
      "cached_display_name": "New Shot 7650",
      "code": "New Shot 7650",
      "sg_status_list": "wtg",
      "sg_shot_type": "VFX",
      "created_at": "2026-09-04 03:51:48 UTC",
      "open_notes_count": 0
    },
    "relationships": { "parent_shots": { "data": [] } },
    "id": 7650
  }
}
```

Without a project:

```json
{"errors": [{"status": 400, "code": 103,
             "title": "API create() missing 'project' attribute: {\"code\" => \"sh010\"}"}]}
```

With a field that does not exist:

```json
{"errors": [{"status": 400, "code": 103,
             "title": "API create() Shot.sg_not_a_field doesn't exist."}]}
```

**Response codes**

| status | when |
|---|---|
| 201 | created |
| 400 | `API create() missing 'project' attribute` |
| 400 | `API create() Shot.sg_not_a_field doesn't exist.` |

**Edge cases**

- Omitting the identity field is not an error: the server writes `New Shot <id>` and returns 201.
  Nothing is unique, so a re-run of an ingest doubles the rows rather than failing.
- `?fields=code` returns 10 attribute keys, not one. Every write ignores it, so re-read the row when you
  need a dotted path or a narrowed set.
- An unknown field **is** a 400 here, unlike an unknown `fields` name on a read, which is dropped at
  200. Writes are loud about names; reads are silent.
- `created_at` comes back as `2026-09-04 03:51:48 UTC`, space separated, where a read returns
  `2026-09-04T03:51:48Z`. The same instant in two formats depending on the call.

**Links**

- `endpoints/post_entity_batch`
- `endpoints/get_entity_type_id`
- `entity_types/Shot`
- `findings/012_create_version`
- `findings/024_read_after_write`