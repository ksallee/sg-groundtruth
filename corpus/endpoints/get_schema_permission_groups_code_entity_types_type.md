---
endpoint: GET /schema/permission_groups/<code>/entity_types/<Type>
coverage: measured
tags: [schema, permission, discovery]
scope: api
measured: site-wide; the script (probe 119), an Admin and an Artist via sudo, every group on six types (probes 132, 143)
verdict: One permission group's rights on one entity type's rows: read, create, update, retire, delete, each `allowed`, `denied` or `conditional`. Nothing about changing the schema.
---

# GET /schema/permission_groups/<code>/entity_types/<Type>

**Params**

| part | value |
|---|---|
| `<code>` | a group's `code` from `GET /schema/permission_groups` |
| `<Type>` | the entity type |
| `permission_rule_set_entity_type` | optional, `HumanUser` or `ApiUser` |

**Sample requests**

```python
r = c.get("/schema/permission_groups/api_admin/entity_types/Version")
```

```json
{
  "data": {
    "permission_group": {"id": "<id>", "code": "api_admin", "display_name": "API Admin", "entity_type": "ApiUser"},
    "entity_type": "Version",
    "permissions": {"set_id": "<id>", "code": "api_admin", "display_name": "API Admin",
                    "see": true, "create": true, "retire": true, "update_field_generic": true},
    "actions": {"read": {"access": "allowed"}, "create": {"access": "allowed"},
                "update": {"access": "allowed"}, "retire": {"access": "allowed"},
                "delete": {"access": "allowed"}}
  },
  "links": {"self": "/api/v1/schema/permission_groups/api_admin/entity_types/Version"}
}
```

```python
r = c.get("/schema/permission_groups/artist/entity_types/Version")
```

```json
{"errors": [{"status": 404, "code": 103, "title": "Not Found",
             "detail": "Unknown permission group code 'artist'"}]}
```

An update with exceptions, read by an Admin person for the `vendor` group on Attachment (probe 143):

```json
"actions": {"read": {"access": "conditional"}, "create": {"access": "allowed"},
            "update": {"access": "conditional", "field_exceptions": {"allow": ["attachment_links", "project"], "deny": []}},
            "retire": {"access": "denied"}, "delete": {"access": "denied"}}
```

**Response codes**

| status | when |
|---|---|
| 200 | the group is one the caller may inspect |
| 404 | `Unknown permission group code '<code>'`, for a group the caller may not inspect as well as one that does not exist |
| 404 | `Entity type 'DisplayColumn' does not exist.` |

**Edge cases**

- The actions are about rows. No key reports whether the group may create, update or retire a field.
- A group the caller cannot see is reported as unknown, not as forbidden.
- An Admin person reads every group; an Artist only its own (probe 132). An Artist's answers matched
  every refusal it got on custom-entity rows and Attachments (probe 143), so this is the preflight to
  read before writing as a person.
- `update.field_exceptions` lists the fields an update rule allows or denies against the type's
  default, e.g. `allow: ["sg_status_list"]` where `update` is `denied`.

**Links**

- `endpoints/get_schema_permission_groups`
- `findings/119_field_absent_retired_live`
- `findings/094_permission_preflight`
