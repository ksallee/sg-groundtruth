---
endpoint: PUT /preferences/custom_entity/<entity_type>/configuration
coverage: partial
unmeasured: the success path. The probed site answers 400 code 111 to every body, so the request and response shapes are /spec.json's and unverified. Blocked on the site.
tags: [custom-entity, write, error-handling, discovery]
scope: api
measured: site-wide, bodies with no keys only, probe 114
verdict: Sets an enabled custom entity slot's display name and feature flags, per /spec.json. On the probed site every call answered 400 code 111.
---

# PUT /preferences/custom_entity/<entity_type>/configuration

It is in `/spec.json` and in no published reference. Everything in **Params** is the spec's account,
not a measurement.

**Params**

| part | value |
|---|---|
| `<entity_type>` | singular CamelCase, `CustomEntity01` |
| body `display_name` | optional. The label the site shows for the slot |
| body `entity_config` | optional. Any of `enable_tasks`, `enable_versions`, `enable_publishes`, `enable_detail_page`, `include_in_search`, `include_in_global_menu`, each a boolean |
| omitted keys | left unchanged, per the spec |

**Sample requests**

A body with no keys, on an enabled slot:

```python
r = c.put("/preferences/custom_entity/CustomEntity01/configuration", json={})
```

```json
[{"id": "5ff241a6-dc04-42eb-9bd7-aba3510fc9f4", "status": 400, "code": 111,
  "title": "Custom entity configuration through the API is not available", "source": null,
  "detail": null, "meta": null}]
```

**Response codes**

| status | when |
|---|---|
| 200 | per the spec: updated, and the body is the slot's `entity_type`, `enabled`, `display_name` and `entity_config`. Not reached |
| 400 | code 111, `Custom entity configuration through the API is not available`. Every call on the probed site |
| 401 | per the spec: invalid credentials |
| 403 | per the spec: `Custom entity configuration feature is not enabled`. The probed site answers 400 instead |
| 404 | per the spec: `Record does not exist.` |
| 422 | per the spec: `Entity has not been enabled yet.` Not reached: a slot absent from `GET /schema` answered the 400 |

**Edge cases**

- It does not enable a slot. The spec sends that to the `/activation` call.
- Only bodies with no keys were sent, so a site where the call is available would have changed nothing.

**Links**

- `endpoints/get_preferences_custom_entity_entity_type_configuration`
- `endpoints/put_preferences_custom_entity_entity_type_activation`
- `findings/114_schema_admin_recheck`
