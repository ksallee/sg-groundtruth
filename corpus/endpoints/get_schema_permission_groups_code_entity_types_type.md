---
endpoint: GET /schema/permission_groups/<code>/entity_types/<Type>
coverage: measured
tags: [schema, permission, discovery]
scope: api
measured: site-wide; the script, an Admin, an Artist and a Vendor via sudo, every group on six types (probes 119-162)
verdict: One permission group's rights on one entity type's rows: read, create, update, retire, delete, each `allowed`, `denied` or `conditional`, a conditional one with its filter tree. Read only.
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

A conditional read, the `vendor` group on Shot as an Admin person reads it (probe 162, trimmed). The
raw `permissions.see_condition` holds the same tree:

```json
"read": {"access": "conditional", "condition": {"logical_operator": "or", "conditions": [
  {"path": "sg_vendor_groups.Group.users", "relation": "is",
   "values": [{"type": "HumanUser", "id": 0, "valid": "logged_in_user_token", "name": "Me"}]},
  {"path": "sg_vendor_groups.Group.sg_people", "relation": "is", "values": ["<the same token>"]}]}}
```

**Response codes**

| status | when |
|---|---|
| 200 | the group is one the caller may inspect |
| 404 | `Unknown permission group code '<code>'`, for a group the script may not inspect as well as one that does not exist |
| 403 | code 102 `Insufficient permissions to read this permission group configuration`, a person asking for another group (probe 162) |
| 404 | `PUT`, `POST` or `PATCH` on the route, code 103 `Not Found`: there is no write (probe 162) |
| 404 | `Entity type 'DisplayColumn' does not exist.` |

**Edge cases**

- The actions are about rows. No key reports whether the group may create, update or retire a field.
- A group the caller cannot see is reported as unknown, not as forbidden.
- An Admin person reads every group; an Artist only its own (probe 132). An Artist's answers matched
  every refusal it got on custom-entity rows and Attachments (probe 143), so this is the preflight to
  read before writing as a person.
- `update.field_exceptions` lists the fields an update rule allows or denies against the type's
  default, e.g. `allow: ["sg_status_list"]` where `update` is `denied`.
- A `conditional` action has `condition`, a filter tree in the `_search` hash shape. The signed-in
  person is `{"valid": "logged_in_user_token", "id": 0}` when an Admin reads it, and the caller's own
  `{"type": "HumanUser", "id": <me>, "valid": "valid"}` when a person reads their own group, whose
  `field_exceptions` also drops the empty `deny` list (probe 162). Match both forms.

**Links**

- `endpoints/get_schema_permission_groups`
- `findings/119_field_absent_retired_live`
- `findings/094_permission_preflight`
