---
endpoint: GET /schema/permission_groups
coverage: partial
unmeasured: the call as a person, and as a caller with `set_permissions`. Only the script was measured. Blocked on the site: it needs that person's session.
tags: [schema, permission, discovery]
scope: api
measured: site-wide, as the script, probe 119
verdict: Lists the permission groups the caller may inspect. The script saw one, its own `api_admin`, and no HumanUser group. In `/spec.json` since 2026-11-10, in no reference page.
---

# GET /schema/permission_groups

**Params**

| part | value |
|---|---|
| `permission_rule_set_entity_type` | optional, `HumanUser` or `ApiUser`. Defaults to the caller's own kind |

**Sample requests**

```python
r = c.get("/schema/permission_groups")
```

```json
{
  "data": [{"id": "<id>", "code": "api_admin", "display_name": "API Admin", "entity_type": "ApiUser",
            "parent_set_id": null, "updated_at": "<timestamp>"}],
  "links": {"self": "/api/v1/schema/permission_groups"}
}
```

```python
r = c.get("/schema/permission_groups", params={"permission_rule_set_entity_type": "HumanUser"})
```

```json
{"data": [], "links": {"self": "/api/v1/schema/permission_groups?permission_rule_set_entity_type=HumanUser"}}
```

**Response codes**

| status | when |
|---|---|
| 200 | always seen, with an empty `data` for a kind the caller may not inspect |

**Edge cases**

- `/spec.json` says a caller without `set_permissions` sees only its own group. The script, an API
  Admin, got its own group and an empty list for `HumanUser`.
- `code` is what the two child calls take in their path.

**Links**

- `endpoints/get_schema_permission_groups_code_entity_types_type`
- `endpoints/get_schema_permission_groups_code_entity_types_type_fields`
- `findings/119_field_absent_retired_live`
- `findings/027_auth_permissions`
