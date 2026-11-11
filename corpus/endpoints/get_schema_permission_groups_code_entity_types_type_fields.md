---
endpoint: GET /schema/permission_groups/<code>/entity_types/<Type>/fields
coverage: partial
unmeasured: a group other than the caller's own, and `status_transitions` on a status field. Only `api_admin` was readable. Blocked on the site.
tags: [schema, permission, discovery]
scope: api
measured: site-wide, as the script, probe 119
verdict: One permission group's `see` and `update` right on every field of an entity type, as a list. It is about field values, not about changing the field's definition.
---

# GET /schema/permission_groups/<code>/entity_types/<Type>/fields

**Params**

| part | value |
|---|---|
| `<code>` | a group's `code` from `GET /schema/permission_groups` |
| `<Type>` | the entity type |
| `permission_rule_set_entity_type` | optional, `HumanUser` or `ApiUser` |

**Sample requests**

```python
r = c.get("/schema/permission_groups/api_admin/entity_types/Version/fields")
```

On the probed site, 73 fields in 17164 bytes:

```json
{
  "data": {
    "permission_group": {"id": "<id>", "code": "api_admin", "display_name": "API Admin", "entity_type": "ApiUser"},
    "entity_type": "Version",
    "fields": [
      {"field_name": "sg_my_field", "display_name": "My Field",
       "permissions": {"set_id": "<id>", "code": "api_admin", "display_name": "API Admin", "see": true, "update": true},
       "see": {"access": "allowed"}, "update": {"access": "allowed"}}
    ]
  }
}
```

**Response codes**

| status | when |
|---|---|
| 200 | the group is one the caller may inspect |
| 404 | `Unknown permission group code '<code>'` |

**Edge cases**

- `fields` is a list, where `GET /schema/<Type>/fields` is an object keyed by field name.
- On the probed site it lists 73 fields on Version where `GET /schema/Version/fields` lists 71.
  Which two differ was not recorded.

**Links**

- `endpoints/get_schema_permission_groups`
- `endpoints/get_schema_type_fields`
- `findings/119_field_absent_retired_live`
