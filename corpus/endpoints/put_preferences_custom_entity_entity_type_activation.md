---
endpoint: PUT /preferences/custom_entity/<entity_type>/activation
coverage: partial
unmeasured: the success path. The probed site answers 400 code 111 to every body, so the request and response shapes are /spec.json's and unverified. Blocked on the site.
tags: [custom-entity, write, error-handling, discovery]
scope: api
measured: site-wide, rejections only, probe 114
verdict: Enables or disables a custom entity slot, per /spec.json. On the probed site every call answered 400 code 111 `Custom entity configuration through the API is not available`.
---

# PUT /preferences/custom_entity/<entity_type>/activation

Sets whether a `CustomEntityNN` slot is enabled. It is in `/spec.json` and in no published reference.
Everything in **Params** is the spec's account, not a measurement.

**Params**

| part | value |
|---|---|
| `<entity_type>` | singular CamelCase, `CustomEntity01` |
| body `enabled` | required. A JSON boolean. The spec says the string `"true"` is rejected |
| body `force` | optional, only with `enabled: false`. `true` disables a slot that still has records. The spec says it is a 400 with `enabled: true` |

**Sample requests**

```python
r = c.put("/preferences/custom_entity/NotAnEntityType/activation", json={"enabled": True})
```

```json
[{"id": "57487fe6-a86d-4731-a2db-223cbe05cac4", "status": 400, "code": 111,
  "title": "Custom entity configuration through the API is not available", "source": null,
  "detail": null, "meta": null}]
```

A body without `enabled`, on a slot absent from `GET /schema`, answers the same:

```python
r = c.put("/preferences/custom_entity/CustomEntity50/activation", json={})
# 400, code 111, the same title
```

**Response codes**

| status | when |
|---|---|
| 200 | per the spec: the state was applied, and the body is the slot's `entity_type`, `enabled`, `display_name` and `entity_config`. Not reached |
| 400 | code 111, `Custom entity configuration through the API is not available`. Every call on the probed site |
| 401 | per the spec: invalid credentials |
| 403 | per the spec: `Custom entity configuration feature is not enabled`. The probed site answers 400 instead |
| 404 | `GET` on this path. The spec names no read here |

**Edge cases**

- The 400 precedes validation. A type that does not exist and a body with no keys get the same answer
  as a complete request, so the error says nothing about the slot or the body.
- The spec says disabling a slot makes its records unreachable through the web interface and the API,
  and leaves link fields that point at them as broken references. It refuses a slot with live records
  unless `force` is `true`.
- No success was attempted on a real slot. A site where this call is available changes its schema for
  every user when it succeeds.

**Links**

- `endpoints/get_preferences_custom_entity_entity_type_configuration`
- `endpoints/put_preferences_custom_entity_entity_type_configuration`
- `endpoints/put_preferences_update`
- `findings/114_schema_admin_recheck`
- `findings/008_custom_entities`
