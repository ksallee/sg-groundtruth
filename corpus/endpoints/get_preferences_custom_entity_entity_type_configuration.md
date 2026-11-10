---
endpoint: GET /preferences/custom_entity/<entity_type>/configuration
coverage: partial
unmeasured: the success path. The probed site answers 400 code 111 for every type, so the response shape is /spec.json's and unverified. Blocked on the site.
tags: [custom-entity, error-handling, discovery]
scope: api
measured: site-wide, rejections only, probe 114
verdict: Reads one custom entity slot's enabled state, display name and feature flags, per /spec.json. On the probed site every type answered 400 code 111.
---

# GET /preferences/custom_entity/<entity_type>/configuration

It is in `/spec.json` and in no published reference. The response fields below are the spec's account,
not a measurement.

**Params**

| part | value |
|---|---|
| `<entity_type>` | singular CamelCase, `CustomEntity01` |

**Sample requests**

```python
r = c.get("/preferences/custom_entity/CustomEntity01/configuration")
```

```json
[{"id": "df4bbf10-1f02-4b5c-8905-f780f960a66a", "status": 400, "code": 111,
  "title": "Custom entity configuration through the API is not available", "source": null,
  "detail": null, "meta": null}]
```

**Response codes**

| status | when |
|---|---|
| 200 | per the spec: `entity_type`, `enabled`, `display_name`, and `entity_config` when enabled. Not reached |
| 400 | code 111, `Custom entity configuration through the API is not available`. Every call on the probed site |
| 401 | per the spec: invalid credentials |
| 403 | per the spec: `Custom entity configuration feature is not enabled`. The probed site answers 400 instead |
| 404 | per the spec: `Record does not exist.` Also `GET /preferences/custom_entity`, which lists nothing |

**Edge cases**

- On the probed site an enabled slot, a slot absent from `GET /schema`, `Shot` and a type that does not
  exist all answered the same 400. The refusal precedes any look at the type.
- `entity_config` in the spec holds six booleans: `enable_tasks`, `enable_versions`,
  `enable_publishes`, `enable_detail_page`, `include_in_search`, `include_in_global_menu`.
- Until this answers 200, read which slots are enabled from `GET /schema` (probe 008).

**Links**

- `endpoints/put_preferences_custom_entity_entity_type_configuration`
- `endpoints/put_preferences_custom_entity_entity_type_activation`
- `endpoints/get_schema`
- `findings/114_schema_admin_recheck`
